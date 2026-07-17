import base64
import hashlib
import json
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import quote_plus, urlencode
from urllib.request import ProxyHandler, Request, build_opener
from urllib.error import HTTPError

# Bypass Windows system proxy (e.g. Clash 127.0.0.1:7890) which breaks payment HTTPS.
# Set PAYMENT_HTTP_PROXY to force an explicit proxy when needed.
_payment_opener = None


def _payment_urlopen(req: Request, timeout: int = 10):
    global _payment_opener
    proxy = (os.environ.get("PAYMENT_HTTP_PROXY") or "").strip()
    if proxy:
        opener = build_opener(ProxyHandler({"http": proxy, "https": proxy}))
        return opener.open(req, timeout=timeout)
    if _payment_opener is None:
        _payment_opener = build_opener(ProxyHandler({}))
    return _payment_opener.open(req, timeout=timeout)

from django.utils import timezone as dj_timezone

try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:  # pragma: no cover
    x509 = None
    default_backend = None
    hashes = None
    serialization = None
    padding = None
    AESGCM = None


@dataclass
class CreatePaymentResult:
    ok: bool
    message: str
    payment_url: str = ""
    payment_mode: str = "qr"
    expires_at: datetime | None = None
    provider_trade_no: str = ""
    provider_payload: dict | None = None


@dataclass
class NotifyParseResult:
    ok: bool
    message: str
    out_trade_no: str = ""
    provider_trade_no: str = ""
    paid: bool = False
    raw_payload: dict | None = None


@dataclass
class RefundResult:
    ok: bool
    message: str
    provider_refund_no: str = ""
    provider_payload: dict | None = None


def _project_base_dir() -> str:
    try:
        from django.conf import settings as dj_settings

        return str(getattr(dj_settings, "BASE_DIR", "") or "")
    except Exception:
        return ""


def _load_secret_from_env_or_file(raw: str) -> str:
    """
    Resolve secret material from env. Supported forms:
    - PEM/plain text inline
    - Absolute or relative path to a PEM file on disk (if the path exists and is a file)
    - Relative path under Django BASE_DIR (e.g. secrets/apiclient_key.pem)
    - file://absolute/or/relative/path.pem
    - b64:<base64-encoded PEM or secret string>
    """
    value = (raw or "").strip()
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1].strip()
    if value.startswith("file://"):
        path = value[len("file://") :].strip()
        if not path:
            return ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return ""
    if value.startswith("b64:"):
        encoded = value[len("b64:") :].strip()
        try:
            return base64.b64decode(encoded).decode("utf-8").strip()
        except Exception:
            return ""
    path_candidates = [os.path.expanduser(value)]
    base_dir = _project_base_dir()
    if base_dir and not os.path.isabs(value):
        path_candidates.append(os.path.join(base_dir, value))
    for path_candidate in path_candidates:
        if os.path.isfile(path_candidate):
            try:
                with open(path_candidate, "r", encoding="utf-8") as f:
                    text = f.read().strip()
                    if "\\n" in text and "-----BEGIN" in text:
                        text = text.replace("\\n", "\n")
                    return text
            except Exception:
                return ""
    if "\\n" in value and "-----BEGIN" in value:
        return value.replace("\\n", "\n")
    return value


def _sign_with_rsa_sha256(content: str, private_key_pem: str) -> str:
    if not (serialization and hashes and padding and default_backend):
        raise RuntimeError("cryptography_missing")
    raw = (private_key_pem or "").strip()
    try:
        key = serialization.load_pem_private_key(
            raw.encode("utf-8"), password=None, backend=default_backend()
        )
    except Exception as e:
        # Compatibility: support one-line base64 DER private key content.
        try:
            der = base64.b64decode(raw, validate=True)
            key = serialization.load_der_private_key(der, password=None, backend=default_backend())
        except Exception:
            raise RuntimeError(f"invalid_private_key_format:{str(e)[:200]}") from e
    sign = key.sign(content.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sign).decode("utf-8")


def _verify_rsa_sha256(content: str, signature_b64: str, public_key_pem: str) -> bool:
    if not (serialization and hashes and padding and default_backend):
        return False
    raw = (public_key_pem or "").strip()
    try:
        try:
            key = serialization.load_pem_public_key(raw.encode("utf-8"), backend=default_backend())
        except Exception:
            der = base64.b64decode(raw, validate=True)
            key = serialization.load_der_public_key(der, backend=default_backend())
        key.verify(base64.b64decode(signature_b64), content.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
        return True
    except Exception:
        return False


def _http_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 10) -> dict:
    # Must match compact JSON used in WeChat Pay v3 Authorization sign string (no spaces after ':').
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    req_headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    req = Request(url=url, data=data, method="POST", headers=req_headers)
    try:
        with _payment_urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = (getattr(resp.headers, "get_content_charset", lambda: None)() or "").strip()
            text = ""
            for enc in [charset, "utf-8", "gb18030", "gbk", "latin-1"]:
                if not enc:
                    continue
                try:
                    text = raw.decode(enc)
                    break
                except Exception:
                    continue
            if not text:
                text = raw.decode("utf-8", errors="replace")
            text = (text or "").lstrip("\ufeff").strip()
            if not text:
                raise ValueError("empty_response_body")
            return json.loads(text)
    except HTTPError as e:
        raw = b""
        try:
            raw = e.read() or b""
        except Exception:
            raw = b""
        body = raw.decode("utf-8", errors="replace").strip() if raw else ""
        body_preview = body[:500].replace("\r", "\\r").replace("\n", "\\n")
        raise RuntimeError(f"http_error:{getattr(e, 'code', '')}:{body_preview or str(e)}") from e


def _decode_http_body(resp, raw: bytes) -> str:
    charset = (getattr(resp.headers, "get_content_charset", lambda: None)() or "").strip()
    for enc in [charset, "utf-8", "gb18030", "gbk", "latin-1"]:
        if not enc:
            continue
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")


def _to_cst_time_str(dt: datetime) -> str:
    dt = dt.astimezone(timezone(timedelta(hours=8)))
    return dt.strftime("%Y-%m-%d %H:%M:%S")


_ALIPAY_NAME_OID_SHORT = {
    x509.NameOID.COUNTRY_NAME: "C",
    x509.NameOID.ORGANIZATION_NAME: "O",
    x509.NameOID.ORGANIZATIONAL_UNIT_NAME: "OU",
    x509.NameOID.COMMON_NAME: "CN",
} if x509 else {}


def _format_x509_name_for_alipay(name) -> str:
    parts: list[str] = []
    for rdn in reversed(list(name)):
        # cryptography >=42 iterates Name as NameAttribute; older versions use RelativeDistinguishedName.
        attrs = [rdn] if isinstance(rdn, x509.NameAttribute) else list(rdn)
        for attr in attrs:
            short = _ALIPAY_NAME_OID_SHORT.get(attr.oid)
            if short:
                parts.append(f"{short}={attr.value}")
    return ",".join(parts)


def _alipay_cert_sn_from_pem(cert_pem: str) -> str:
    if not x509:
        raise RuntimeError("cryptography_missing")
    cert = x509.load_pem_x509_certificate(cert_pem.encode("utf-8"), default_backend())
    issuer = _format_x509_name_for_alipay(cert.issuer)
    return hashlib.md5(f"{issuer}{cert.serial_number}".encode("utf-8")).hexdigest()


def _alipay_root_cert_sn_from_pem(root_cert_pem: str) -> str:
    if not x509:
        raise RuntimeError("cryptography_missing")
    chunks = root_cert_pem.replace("\r\n", "\n").split("-----END CERTIFICATE-----")
    sns: list[str] = []
    for chunk in chunks:
        text = chunk.strip()
        if not text or "-----BEGIN CERTIFICATE-----" not in text:
            continue
        pem = f"{text}\n-----END CERTIFICATE-----\n"
        cert = x509.load_pem_x509_certificate(pem.encode("utf-8"), default_backend())
        sig_name = cert.signature_algorithm_oid._name
        if sig_name not in ("sha1WithRSAEncryption", "sha256WithRSAEncryption"):
            continue
        sns.append(_alipay_cert_sn_from_pem(pem))
    if not sns:
        raise RuntimeError("alipay_root_cert_sn_empty")
    return "_".join(sns)


def _alipay_cert_config_hint() -> str:
    app_cert_path = os.environ.get("ALIPAY_APP_CERT", "").strip()
    root_cert_path = os.environ.get("ALIPAY_ROOT_CERT", "").strip()
    if app_cert_path:
        expanded = os.path.expanduser(app_cert_path)
        if not os.path.isfile(expanded):
            return f"ALIPAY_APP_CERT 文件不存在: {expanded}"
    if root_cert_path:
        expanded = os.path.expanduser(root_cert_path)
        if not os.path.isfile(expanded):
            return f"ALIPAY_ROOT_CERT 文件不存在: {expanded}"
    return (
        "转账接口须公钥证书模式：从支付宝开放平台-应用详情-开发设置-接口加签方式 下载"
        "「应用公钥证书 appCertPublicKey_*.crt」与「支付宝根证书 alipayRootCert.crt」，"
        "配置 ALIPAY_APP_CERT、ALIPAY_ROOT_CERT 路径，或直接配置 ALIPAY_APP_CERT_SN、ALIPAY_ROOT_CERT_SN"
    )


def _get_alipay_cert_sn_params() -> dict[str, str]:
    app_cert_sn = os.environ.get("ALIPAY_APP_CERT_SN", "").strip()
    root_cert_sn = os.environ.get("ALIPAY_ROOT_CERT_SN", "").strip()
    if not app_cert_sn:
        app_cert_pem = _load_secret_from_env_or_file(os.environ.get("ALIPAY_APP_CERT", ""))
        if app_cert_pem:
            try:
                app_cert_sn = _alipay_cert_sn_from_pem(app_cert_pem)
            except Exception:
                app_cert_sn = ""
    if not root_cert_sn:
        root_cert_pem = _load_secret_from_env_or_file(os.environ.get("ALIPAY_ROOT_CERT", ""))
        if root_cert_pem:
            try:
                root_cert_sn = _alipay_root_cert_sn_from_pem(root_cert_pem)
            except Exception:
                root_cert_sn = ""
    if app_cert_sn and root_cert_sn:
        return {"app_cert_sn": app_cert_sn, "alipay_root_cert_sn": root_cert_sn}
    return {}


def _wechat_transfer_id(raw: str, *, max_len: int = 32) -> str:
    """微信商家批次/明细单号仅允许数字和字母。"""
    cleaned = "".join(ch for ch in (raw or "").strip() if ch.isalnum())
    if len(cleaned) >= 6:
        return cleaned[:max_len]
    return secrets.token_hex(max_len // 2)[:max_len]


def _alipay_sign_params(params: dict, app_private_key: str) -> str:
    sign_src = "&".join(
        f"{k}={v}"
        for k, v in sorted(params.items(), key=lambda item: item[0])
        if v is not None and v != "" and k != "sign"
    )
    return _sign_with_rsa_sha256(sign_src, app_private_key)


def _create_alipay_order(
    *,
    out_trade_no: str,
    amount: Decimal,
    notify_url: str,
    subject: str = "",
) -> CreatePaymentResult:
    app_id = os.environ.get("ALIPAY_APP_ID", "").strip()
    gateway = os.environ.get("ALIPAY_GATEWAY", "https://openapi.alipay.com/gateway.do").strip()
    app_private_key = _load_secret_from_env_or_file(os.environ.get("ALIPAY_APP_PRIVATE_KEY", ""))
    alipay_public_key = _load_secret_from_env_or_file(os.environ.get("ALIPAY_PUBLIC_KEY", ""))
    if not all([app_id, gateway, app_private_key, alipay_public_key]):
        return CreatePaymentResult(ok=False, message="alipay_config_missing")

    expires_at = dj_timezone.now() + timedelta(minutes=2)
    biz_content = {
        "out_trade_no": out_trade_no,
        "total_amount": f"{Decimal(amount):.2f}",
        "subject": (subject or f"Recharge{out_trade_no}")[:256],
        "timeout_express": "2m",
    }
    params = {
        "app_id": app_id,
        "method": "alipay.trade.precreate",
        "format": "JSON",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": _to_cst_time_str(datetime.now(timezone.utc)),
        "version": "1.0",
        "notify_url": notify_url,
        "biz_content": json.dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
    }
    params.update(_get_alipay_cert_sn_params())
    try:
        params["sign"] = _alipay_sign_params(params, app_private_key)
    except Exception as e:
        return CreatePaymentResult(ok=False, message=f"alipay_sign_failed:{str(e)[:220]}")
    query = "&".join(f"{k}={quote_plus(str(v))}" for k, v in params.items())
    post_data = urlencode(params).encode("utf-8")
    try:
        req = Request(
            url=gateway,
            data=post_data,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                "Accept": "application/json,text/plain,*/*",
                "User-Agent": "haixuan-voting-payment/1.0",
            },
        )
        with _payment_urlopen(req, timeout=12) as resp:
            raw = resp.read()
            text = _decode_http_body(resp, raw)
            text = (text or "").lstrip("\ufeff").strip()
            if not text:
                return CreatePaymentResult(ok=False, message="alipay_create_empty_response")
            try:
                payload = json.loads(text)
            except Exception:
                preview = text[:220].replace("\r", "\\r").replace("\n", "\\n")
                status = getattr(resp, "status", None)
                final_url = getattr(resp, "url", gateway)
                return CreatePaymentResult(
                    ok=False,
                    message=f"alipay_create_non_json_response:status={status},url={final_url},body={preview}",
                )
    except Exception as e:
        return CreatePaymentResult(ok=False, message=f"alipay_create_failed:{str(e)[:220]}")
    result = payload.get("alipay_trade_precreate_response") or {}
    if result.get("code") != "10000":
        return CreatePaymentResult(ok=False, message=f"alipay_create_rejected:{result.get('sub_msg') or result.get('msg') or 'unknown'}")
    qr_code = (result.get("qr_code") or "").strip()
    if not qr_code:
        return CreatePaymentResult(ok=False, message="alipay_qr_missing")
    return CreatePaymentResult(
        ok=True,
        message="ok",
        payment_url=qr_code,
        payment_mode="qr",
        expires_at=expires_at,
        provider_trade_no=(result.get("trade_no") or "").strip(),
        provider_payload=payload,
    )


def _create_wechat_order(
    *,
    out_trade_no: str,
    amount: Decimal,
    notify_url: str,
    description: str = "",
) -> CreatePaymentResult:
    """
    WeChat Pay APIv3 Native 下单。

    - 直连商户：/v3/pay/transactions/native，Authorization 里的 mchid 须与证书商户号一致。
    - 服务商模式：/v3/pay/partner/transactions/native，Authorization 里的 mchid 必须是 **sp_mchid**
      （即持有 WECHAT_PAY_MCH_PRIVATE_KEY / serial 的服务商商户号），不能用子商户号，否则会 SIGN_ERROR。
    """
    serial_no = os.environ.get("WECHAT_PAY_MCH_SERIAL_NO", "").strip()
    private_key = _load_secret_from_env_or_file(os.environ.get("WECHAT_PAY_MCH_PRIVATE_KEY", ""))
    api_v3_key = _load_secret_from_env_or_file(os.environ.get("WECHAT_PAY_API_V3_KEY", ""))

    sub_mchid = (os.environ.get("WECHAT_PAY_SUB_MCH_ID") or "").strip()
    sp_mchid = (os.environ.get("WECHAT_PAY_SP_MCH_ID") or "").strip()
    sp_appid = (os.environ.get("WECHAT_PAY_SP_APP_ID") or "").strip()
    sub_appid = (os.environ.get("WECHAT_PAY_SUB_APP_ID") or "").strip()
    mchid_direct = (os.environ.get("WECHAT_PAY_MCH_ID") or "").strip()
    appid_direct = (os.environ.get("WECHAT_PAY_APP_ID") or "").strip()
    desc = (description or f"Recharge {out_trade_no}")[:127]

    partner_mode = bool(sub_mchid)
    if partner_mode:
        sp_mchid = sp_mchid or mchid_direct
        sp_appid = sp_appid or appid_direct
        if not all([sp_mchid, sp_appid, sub_mchid, serial_no, private_key, api_v3_key]):
            return CreatePaymentResult(ok=False, message="wechat_config_missing_partner")
        auth_mchid = sp_mchid
        expires_at = dj_timezone.now() + timedelta(minutes=2)
        body: dict = {
            "sp_appid": sp_appid,
            "sp_mchid": sp_mchid,
            "sub_mchid": sub_mchid,
            "description": desc,
            "out_trade_no": out_trade_no,
            "notify_url": notify_url,
            "amount": {"total": int(Decimal(amount) * 100), "currency": "CNY"},
            "time_expire": expires_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        if sub_appid:
            body["sub_appid"] = sub_appid
        request_path = "/v3/pay/partner/transactions/native"
        url = "https://api.mch.weixin.qq.com/v3/pay/partner/transactions/native"
    else:
        if not all([mchid_direct, appid_direct, serial_no, private_key, api_v3_key]):
            return CreatePaymentResult(ok=False, message="wechat_config_missing")
        auth_mchid = mchid_direct
        expires_at = dj_timezone.now() + timedelta(minutes=2)
        body = {
            "appid": appid_direct,
            "mchid": mchid_direct,
            "description": desc,
            "out_trade_no": out_trade_no,
            "notify_url": notify_url,
            "amount": {"total": int(Decimal(amount) * 100), "currency": "CNY"},
            "time_expire": expires_at.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        request_path = "/v3/pay/transactions/native"
        url = "https://api.mch.weixin.qq.com/v3/pay/transactions/native"

    nonce = secrets.token_hex(16)
    timestamp = str(int(time.time()))
    request_body = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    sign_src = f"POST\n{request_path}\n{timestamp}\n{nonce}\n{request_body}\n"
    signature = _sign_with_rsa_sha256(sign_src, private_key)
    auth = (
        'WECHATPAY2-SHA256-RSA2048 '
        f'mchid="{auth_mchid}",nonce_str="{nonce}",timestamp="{timestamp}",serial_no="{serial_no}",signature="{signature}"'
    )
    try:
        payload = _http_json(
            url,
            body,
            headers={"Authorization": auth},
            timeout=12,
        )
    except Exception as e:
        err = str(e)[:500]
        # WeChat 401 SIGN_ERROR: 私钥与 serial 不匹配、或 Authorization.mchid 与证书商户不一致（服务商须用 sp_mchid）
        if "SIGN_ERROR" in err:
            hint = (
                f"auth_mchid={auth_mchid},serial_no={serial_no},partner={partner_mode};"
                "私钥与 WECHAT_PAY_MCH_SERIAL_NO 须为同一套 API 证书；"
                "服务商模式须配置 WECHAT_PAY_SUB_MCH_ID，且 Authorization 使用服务商 sp_mchid"
            )
            return CreatePaymentResult(
                ok=False,
                message=f"wechat_create_failed:sign_error:{hint}",
            )
        return CreatePaymentResult(ok=False, message=f"wechat_create_failed:{err[:200]}")
    code_url = (payload.get("code_url") or "").strip()
    if not code_url:
        return CreatePaymentResult(ok=False, message=f"wechat_code_url_missing:{payload}")
    return CreatePaymentResult(
        ok=True,
        message="ok",
        payment_url=code_url,
        payment_mode="native",
        expires_at=expires_at,
        provider_trade_no=(payload.get("transaction_id") or "").strip(),
        provider_payload=payload,
    )


def create_payment_order(
    *,
    channel: str,
    out_trade_no: str,
    amount: Decimal,
    notify_url: str,
    description: str = "",
) -> CreatePaymentResult:
    if channel == "wechat":
        return _create_wechat_order(
            out_trade_no=out_trade_no,
            amount=amount,
            notify_url=notify_url,
            description=description,
        )
    if channel == "alipay":
        return _create_alipay_order(
            out_trade_no=out_trade_no,
            amount=amount,
            notify_url=notify_url,
            subject=description,
        )
    return CreatePaymentResult(ok=False, message="unsupported_channel")


def _create_alipay_refund(
    *,
    out_trade_no: str,
    out_refund_no: str,
    amount: Decimal,
    reason: str = "",
) -> RefundResult:
    biz_content = {
        "out_trade_no": out_trade_no,
        "refund_amount": f"{Decimal(amount):.2f}",
        "out_request_no": out_refund_no[:64],
        "refund_reason": (reason or "修改申请被拒绝")[:256],
    }
    payload, err = _alipay_api_call(method="alipay.trade.refund", biz_content=biz_content)
    if err != "ok":
        return RefundResult(ok=False, message=err)
    result = (payload or {}).get("alipay_trade_refund_response") or {}
    return RefundResult(
        ok=True,
        message="ok",
        provider_refund_no=(result.get("trade_no") or result.get("out_trade_no") or "").strip(),
        provider_payload=payload,
    )


def _create_wechat_refund(
    *,
    out_trade_no: str,
    out_refund_no: str,
    amount: Decimal,
    total_amount: Decimal,
    reason: str = "",
) -> RefundResult:
    serial_no = os.environ.get("WECHAT_PAY_MCH_SERIAL_NO", "").strip()
    private_key = _load_secret_from_env_or_file(os.environ.get("WECHAT_PAY_MCH_PRIVATE_KEY", ""))
    sub_mchid = (os.environ.get("WECHAT_PAY_SUB_MCH_ID") or "").strip()
    sp_mchid = (os.environ.get("WECHAT_PAY_SP_MCH_ID") or "").strip()
    mchid_direct = (os.environ.get("WECHAT_PAY_MCH_ID") or "").strip()
    partner_mode = bool(sub_mchid)
    if partner_mode:
        sp_mchid = sp_mchid or mchid_direct
        if not all([sp_mchid, sub_mchid, serial_no, private_key]):
            return RefundResult(ok=False, message="wechat_config_missing_partner")
        auth_mchid = sp_mchid
    else:
        if not all([mchid_direct, serial_no, private_key]):
            return RefundResult(ok=False, message="wechat_config_missing")
        auth_mchid = mchid_direct

    refund_fen = int(Decimal(amount) * 100)
    total_fen = int(Decimal(total_amount) * 100)
    if refund_fen < 1 or total_fen < refund_fen:
        return RefundResult(ok=False, message="invalid_refund_amount")

    body: dict = {
        "out_trade_no": out_trade_no,
        "out_refund_no": out_refund_no[:64],
        "reason": (reason or "修改申请被拒绝")[:80],
        "amount": {"refund": refund_fen, "total": total_fen, "currency": "CNY"},
    }
    if partner_mode:
        body["sub_mchid"] = sub_mchid

    request_path = "/v3/refund/domestic/refunds"
    url = "https://api.mch.weixin.qq.com/v3/refund/domestic/refunds"
    nonce = secrets.token_hex(16)
    timestamp = str(int(time.time()))
    request_body = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    sign_src = f"POST\n{request_path}\n{timestamp}\n{nonce}\n{request_body}\n"
    signature = _sign_with_rsa_sha256(sign_src, private_key)
    auth = (
        "WECHATPAY2-SHA256-RSA2048 "
        f'mchid="{auth_mchid}",nonce_str="{nonce}",timestamp="{timestamp}",serial_no="{serial_no}",signature="{signature}"'
    )
    try:
        payload = _http_json(url, body, headers={"Authorization": auth}, timeout=15)
    except Exception as e:
        return RefundResult(ok=False, message=f"wechat_refund_failed:{str(e)[:200]}")
    refund_id = (payload.get("refund_id") or "").strip()
    status = (payload.get("status") or "").strip().upper()
    if not refund_id:
        return RefundResult(ok=False, message=f"wechat_refund_missing_id:{payload}")
    if status in {"CLOSED", "ABNORMAL"}:
        return RefundResult(ok=False, message=f"wechat_refund_status:{status}")
    return RefundResult(
        ok=True,
        message="ok",
        provider_refund_no=refund_id,
        provider_payload=payload,
    )


def create_payment_refund(
    *,
    channel: str,
    out_trade_no: str,
    out_refund_no: str,
    amount: Decimal,
    total_amount: Decimal | None = None,
    reason: str = "",
) -> RefundResult:
    total = total_amount if total_amount is not None else amount
    if channel == "wechat":
        return _create_wechat_refund(
            out_trade_no=out_trade_no,
            out_refund_no=out_refund_no,
            amount=amount,
            total_amount=total,
            reason=reason,
        )
    if channel == "alipay":
        return _create_alipay_refund(
            out_trade_no=out_trade_no,
            out_refund_no=out_refund_no,
            amount=amount,
            reason=reason,
        )
    return RefundResult(ok=False, message="unsupported_channel")


def parse_alipay_notify(post_data: dict) -> NotifyParseResult:
    sign = (post_data.get("sign") or "").strip()
    sign_type = (post_data.get("sign_type") or "").strip().upper()
    alipay_public_key = _load_secret_from_env_or_file(os.environ.get("ALIPAY_PUBLIC_KEY", ""))
    if not all([sign, alipay_public_key]) or sign_type != "RSA2":
        return NotifyParseResult(ok=False, message="alipay_invalid_signature")
    unsigned = {k: v for k, v in post_data.items() if k not in ("sign", "sign_type")}
    content = "&".join(f"{k}={unsigned[k]}" for k in sorted(unsigned.keys()))
    if not _verify_rsa_sha256(content, sign, alipay_public_key):
        return NotifyParseResult(ok=False, message="alipay_signature_verify_failed")
    trade_status = (post_data.get("trade_status") or "").strip()
    return NotifyParseResult(
        ok=True,
        message="ok",
        out_trade_no=(post_data.get("out_trade_no") or "").strip(),
        provider_trade_no=(post_data.get("trade_no") or "").strip(),
        paid=trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"),
        raw_payload=dict(post_data),
    )


def parse_wechat_notify(request) -> NotifyParseResult:
    raw_bytes = request.body or b""
    try:
        body_str = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return NotifyParseResult(ok=False, message="invalid_body_encoding")
    try:
        outer = json.loads(body_str or "{}")
    except Exception:
        return NotifyParseResult(ok=False, message="invalid_json_body")
    if not isinstance(outer, dict):
        outer = {}

    body: dict = outer
    raw_payload: dict = outer

    resource = outer.get("resource")
    if isinstance(resource, dict) and (resource.get("ciphertext") or "").strip():
        # Native / v3 支付结果通知：明文订单字段在 AEAD_AES_256_GCM 解密后的 JSON 内。
        if not AESGCM:
            return NotifyParseResult(ok=False, message="cryptography_aesgcm_missing")
        ts = (request.META.get("HTTP_WECHATPAY_TIMESTAMP") or "").strip()
        nonce_hdr = (request.META.get("HTTP_WECHATPAY_NONCE") or "").strip()
        signature = (request.META.get("HTTP_WECHATPAY_SIGNATURE") or "").strip()
        if not ts or not nonce_hdr or not signature:
            return NotifyParseResult(ok=False, message="wechat_missing_signature_headers")
        platform_pem = _load_secret_from_env_or_file(os.environ.get("WECHAT_PAY_PLATFORM_PUBLIC_KEY_PEM", ""))
        if not platform_pem.strip():
            platform_pem = _load_secret_from_env_or_file(os.environ.get("WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH", ""))
        if not platform_pem.strip():
            return NotifyParseResult(ok=False, message="wechat_platform_public_key_missing")
        sign_msg = f"{ts}\n{nonce_hdr}\n{body_str}\n"
        if not _verify_rsa_sha256(sign_msg, signature, platform_pem):
            return NotifyParseResult(ok=False, message="wechat_signature_verify_failed")
        api_v3_key = _load_secret_from_env_or_file(os.environ.get("WECHAT_PAY_API_V3_KEY", ""))
        if len(api_v3_key.encode("utf-8")) != 32:
            return NotifyParseResult(ok=False, message="wechat_api_v3_key_invalid")
        try:
            associated_data = (resource.get("associated_data") or "").encode("utf-8")
            nonce_inner = (resource.get("nonce") or "").encode("utf-8")
            ciphertext_b64 = (resource.get("ciphertext") or "").strip()
            plaintext = AESGCM(api_v3_key.encode("utf-8")).decrypt(
                nonce_inner,
                base64.b64decode(ciphertext_b64),
                associated_data,
            )
            inner = json.loads(plaintext.decode("utf-8"))
        except Exception:
            return NotifyParseResult(ok=False, message="wechat_decrypt_failed")
        if not isinstance(inner, dict):
            inner = {}
        body = inner
        raw_payload = {**inner, "wechat_notify_event_type": outer.get("event_type")}

    out_trade_no = ""
    provider_trade_no = ""
    sub_res = body.get("resource") if isinstance(body.get("resource"), dict) else {}
    if sub_res and not (sub_res.get("ciphertext") or "").strip():
        out_trade_no = (sub_res.get("out_trade_no") or body.get("out_trade_no") or "").strip()
        provider_trade_no = (sub_res.get("transaction_id") or body.get("transaction_id") or "").strip()
    else:
        out_trade_no = (body.get("out_trade_no") or "").strip()
        provider_trade_no = (body.get("transaction_id") or "").strip()

    trade_state = (body.get("trade_state") or body.get("trade_status") or "").strip().upper()
    paid = trade_state in ("SUCCESS", "TRADE_SUCCESS")

    if not out_trade_no and isinstance(resource, dict) and not (resource.get("ciphertext") or "").strip():
        out_trade_no = (resource.get("out_trade_no") or outer.get("out_trade_no") or "").strip()
        provider_trade_no = (resource.get("transaction_id") or outer.get("transaction_id") or "").strip()

    transfer_bill_no = (body.get("transfer_bill_no") or "").strip()
    transfer_state = (body.get("state") or "").strip().upper()
    if not out_trade_no:
        out_trade_no = (body.get("out_bill_no") or "").strip()
    if not provider_trade_no:
        provider_trade_no = transfer_bill_no

    if not out_trade_no:
        return NotifyParseResult(ok=False, message="missing_out_trade_no")

    event_type = (outer.get("event_type") or "").strip()
    if event_type == "MCHTRANSFER.BILL.FINISHED":
        paid = transfer_state == "SUCCESS"
    elif isinstance(resource, dict) and (resource.get("ciphertext") or "").strip():
        paid = paid and event_type == "TRANSACTION.SUCCESS"

    if transfer_state:
        raw_payload = {**raw_payload, "state": transfer_state}

    return NotifyParseResult(
        ok=True,
        message="ok",
        out_trade_no=out_trade_no,
        provider_trade_no=provider_trade_no,
        paid=paid,
        raw_payload=raw_payload,
    )


@dataclass
class CreateTransferResult:
    ok: bool
    message: str
    provider_trade_no: str = ""
    provider_payload: dict | None = None
    pending_user_confirm: bool = False
    package_info: str = ""


_WECHAT_TRANSFER_SCENE_REPORTS: dict[str, list[dict[str, str]]] = {
    "1000": [
        {"info_type": "活动名称", "info_content": "海选投票提现"},
        {"info_type": "奖励说明", "info_content": "用户账户余额提现"},
    ],
    "1005": [
        {"info_type": "岗位类型", "info_content": "用户"},
        {"info_type": "报酬说明", "info_content": "海选投票余额提现"},
    ],
}

_ALIPAY_TRANSFER_SCENE_REPORTS: dict[str, list[str]] = {
    "现金营销": ["活动名称", "奖励说明"],
    "企业退款": ["退款原因"],
    "佣金报酬": ["佣金报酬说明"],
    "业务结算": ["结算款项名称"],
    "二手回收": ["回收商品名称"],
    "公益补助": ["公益活动名称"],
    "行政补贴和退款": ["补贴/退款类型"],
    "保险理赔": ["业务类型", "保险险种", "业务交易订单号"],
}


def _wechat_transfer_scene_report_infos(scene_id: str) -> list[dict[str, str]]:
    raw = os.environ.get("WECHAT_PAY_TRANSFER_SCENE_REPORT", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list) and parsed:
                return parsed
        except Exception:
            pass
    return _WECHAT_TRANSFER_SCENE_REPORTS.get(scene_id) or _WECHAT_TRANSFER_SCENE_REPORTS["1005"]


def _alipay_transfer_scene_name() -> str:
    return (os.environ.get("ALIPAY_TRANSFER_SCENE_NAME") or "佣金报酬").strip()


def _alipay_transfer_scene_report_infos(*, scene_name: str, info_content: str) -> list[dict[str, str]]:
    raw = os.environ.get("ALIPAY_TRANSFER_SCENE_REPORT", "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list) and parsed:
                return parsed
        except Exception:
            pass
    info_types = _ALIPAY_TRANSFER_SCENE_REPORTS.get(scene_name)
    if not info_types:
        return [{"info_type": "佣金报酬说明", "info_content": info_content}]
    return [{"info_type": info_type, "info_content": info_content} for info_type in info_types]


def _wechat_platform_serial_no() -> str:
    return (
        os.environ.get("WECHAT_PAY_PLATFORM_SERIAL_NO", "").strip()
        or os.environ.get("WECHAT_PAY_PLATFORM_CERT_SERIAL_NO", "").strip()
    )


def _alipay_api_call(*, method: str, biz_content: dict) -> tuple[dict | None, str]:
    app_id = os.environ.get("ALIPAY_APP_ID", "").strip()
    gateway = os.environ.get("ALIPAY_GATEWAY", "https://openapi.alipay.com/gateway.do").strip()
    app_private_key = _load_secret_from_env_or_file(os.environ.get("ALIPAY_APP_PRIVATE_KEY", ""))
    alipay_public_key = _load_secret_from_env_or_file(os.environ.get("ALIPAY_PUBLIC_KEY", ""))
    if not all([app_id, gateway, app_private_key, alipay_public_key]):
        return None, "alipay_config_missing"
    params = {
        "app_id": app_id,
        "method": method,
        "format": "JSON",
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": _to_cst_time_str(datetime.now(timezone.utc)),
        "version": "1.0",
        "biz_content": json.dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
    }
    params.update(_get_alipay_cert_sn_params())
    try:
        params["sign"] = _alipay_sign_params(params, app_private_key)
    except Exception as e:
        return None, f"alipay_sign_failed:{str(e)[:220]}"
    post_data = urlencode(params).encode("utf-8")
    try:
        req = Request(
            url=gateway,
            data=post_data,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                "Accept": "application/json,text/plain,*/*",
                "User-Agent": "haixuan-voting-payment/1.0",
            },
        )
        with _payment_urlopen(req, timeout=15) as resp:
            raw = resp.read()
            text = _decode_http_body(resp, raw)
            text = (text or "").lstrip("\ufeff").strip()
            if not text:
                return None, "alipay_empty_response"
            payload = json.loads(text)
    except Exception as e:
        return None, f"alipay_request_failed:{str(e)[:220]}"
    response_key = method.replace(".", "_") + "_response"
    result = payload.get(response_key) or {}
    if result.get("code") != "10000":
        return None, f"alipay_rejected:{result.get('sub_msg') or result.get('msg') or 'unknown'}"
    return payload, "ok"


def _create_alipay_transfer(
    *,
    out_biz_no: str,
    amount: Decimal,
    payee_account: str,
    payee_name: str,
) -> CreateTransferResult:
    account = (payee_account or "").strip()
    name = (payee_name or "").strip()
    if not account:
        return CreateTransferResult(ok=False, message="missing_payee_account")
    if not name:
        return CreateTransferResult(ok=False, message="missing_payee_name")
    if not _get_alipay_cert_sn_params():
        return CreateTransferResult(
            ok=False,
            message=f"alipay_cert_sn_missing:{_alipay_cert_config_hint()}",
        )
    biz_content = {
        "out_biz_no": out_biz_no[:64],
        "trans_amount": f"{Decimal(amount):.2f}",
        "product_code": "TRANS_ACCOUNT_NO_PWD",
        "biz_scene": "DIRECT_TRANSFER",
        "order_title": "海选投票提现",
        "payee_info": {
            "identity": account,
            "identity_type": "ALIPAY_LOGON_ID",
            "name": name,
        },
    }
    scene_name = _alipay_transfer_scene_name()
    if scene_name:
        biz_content["transfer_scene_name"] = scene_name
        biz_content["transfer_scene_report_infos"] = _alipay_transfer_scene_report_infos(
            scene_name=scene_name,
            info_content="海选投票余额提现",
        )
    payload, err = _alipay_api_call(method="alipay.fund.trans.uni.transfer", biz_content=biz_content)
    if err != "ok":
        return CreateTransferResult(ok=False, message=err)
    result = (payload or {}).get("alipay_fund_trans_uni_transfer_response") or {}
    return CreateTransferResult(
        ok=True,
        message="ok",
        provider_trade_no=(result.get("order_id") or result.get("pay_fund_order_id") or "").strip(),
        provider_payload=payload,
    )


def _create_wechat_transfer(
    *,
    out_bill_no: str,
    amount: Decimal,
    payee_openid: str,
    payee_name: str = "",
    notify_url: str = "",
) -> CreateTransferResult:
    serial_no = os.environ.get("WECHAT_PAY_MCH_SERIAL_NO", "").strip()
    private_key = _load_secret_from_env_or_file(os.environ.get("WECHAT_PAY_MCH_PRIVATE_KEY", ""))
    api_v3_key = _load_secret_from_env_or_file(os.environ.get("WECHAT_PAY_API_V3_KEY", ""))
    mchid_direct = (os.environ.get("WECHAT_PAY_MCH_ID") or "").strip()
    appid_direct = (os.environ.get("WECHAT_PAY_APP_ID") or "").strip()
    platform_serial = _wechat_platform_serial_no()
    openid = (payee_openid or "").strip()
    if not openid:
        return CreateTransferResult(ok=False, message="missing_payee_openid")
    if not all([mchid_direct, appid_direct, serial_no, private_key, api_v3_key, platform_serial]):
        return CreateTransferResult(
            ok=False,
            message=(
                "wechat_config_missing:新版商家转账还需配置 WECHAT_PAY_PLATFORM_SERIAL_NO"
                "（商户平台-API安全-微信支付公钥-公钥ID）"
            ),
        )
    total_fen = int(Decimal(amount) * 100)
    if total_fen < 1:
        return CreateTransferResult(ok=False, message="amount_too_small")
    scene_id = (os.environ.get("WECHAT_PAY_TRANSFER_SCENE_ID") or "1005").strip()
    bill_no = _wechat_transfer_id(out_bill_no)
    body: dict = {
        "appid": appid_direct,
        "out_bill_no": bill_no,
        "openid": openid,
        "transfer_amount": total_fen,
        "transfer_remark": "海选投票提现",
        "transfer_scene_id": scene_id,
        "transfer_scene_report_infos": _wechat_transfer_scene_report_infos(scene_id),
    }
    transfer_notify_url = (notify_url or os.environ.get("WECHAT_PAY_WALLET_NOTIFY_URL", "")).strip()
    if transfer_notify_url:
        body["notify_url"] = transfer_notify_url
    if scene_id == "1000":
        body["user_recv_perception"] = (os.environ.get("WECHAT_PAY_TRANSFER_USER_RECV_PERCEPTION") or "活动奖励").strip()
    request_path = "/v3/fund-app/mch-transfer/transfer-bills"
    url = "https://api.mch.weixin.qq.com/v3/fund-app/mch-transfer/transfer-bills"
    nonce = secrets.token_hex(16)
    timestamp = str(int(time.time()))
    request_body = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    sign_src = f"POST\n{request_path}\n{timestamp}\n{nonce}\n{request_body}\n"
    signature = _sign_with_rsa_sha256(sign_src, private_key)
    auth = (
        'WECHATPAY2-SHA256-RSA2048 '
        f'mchid="{mchid_direct}",nonce_str="{nonce}",timestamp="{timestamp}",serial_no="{serial_no}",signature="{signature}"'
    )
    try:
        payload = _http_json(
            url,
            body,
            headers={"Authorization": auth, "Wechatpay-Serial": platform_serial},
            timeout=15,
        )
    except Exception as e:
        return CreateTransferResult(ok=False, message=f"wechat_transfer_failed:{str(e)[:200]}")
    transfer_bill_no = (payload.get("transfer_bill_no") or "").strip()
    state = (payload.get("state") or "").strip().upper()
    package_info = (payload.get("package_info") or "").strip()
    if not transfer_bill_no:
        return CreateTransferResult(ok=False, message=f"wechat_transfer_missing_bill_no:{payload}")
    if state == "FAIL":
        fail_reason = (payload.get("fail_reason") or "unknown").strip()
        return CreateTransferResult(ok=False, message=f"wechat_transfer_failed:{fail_reason}")
    pending = state in {"ACCEPTED", "PROCESSING", "WAIT_USER_CONFIRM", "TRANSFERING"}
    if state == "SUCCESS":
        pending = False
    return CreateTransferResult(
        ok=True,
        message="await_user_confirm" if pending else "ok",
        provider_trade_no=transfer_bill_no,
        provider_payload=payload,
        pending_user_confirm=pending,
        package_info=package_info,
    )


def create_payout_transfer(
    *,
    channel: str,
    out_biz_no: str,
    amount: Decimal,
    payee_account: str,
    payee_name: str = "",
    out_detail_no: str = "",
    notify_url: str = "",
) -> CreateTransferResult:
    if Decimal(amount) < Decimal("0.01"):
        return CreateTransferResult(ok=False, message="amount_too_small")
    if channel == "alipay":
        return _create_alipay_transfer(
            out_biz_no=out_biz_no,
            amount=amount,
            payee_account=payee_account,
            payee_name=payee_name,
        )
    if channel == "wechat":
        return _create_wechat_transfer(
            out_bill_no=out_biz_no,
            amount=amount,
            payee_openid=payee_account,
            payee_name=payee_name,
            notify_url=notify_url,
        )
    return CreateTransferResult(ok=False, message="unsupported_channel")


def wechat_transfer_confirm_payload(provider_payload: dict | None) -> dict:
    payload = provider_payload or {}
    package_info = (payload.get("package_info") or "").strip()
    state = (payload.get("state") or "").strip()
    if not package_info and state != "WAIT_USER_CONFIRM":
        return {}
    mch_id = (os.environ.get("WECHAT_PAY_MCH_ID") or "").strip()
    app_id = (os.environ.get("WECHAT_PAY_APP_ID") or "").strip()
    result = {
        "mchId": mch_id,
        "appId": app_id,
        "packageInfo": package_info,
        "transferState": state,
    }
    if package_info:
        result["needUserConfirm"] = True
    return result
