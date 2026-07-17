import mimetypes
from io import BytesIO
from urllib.parse import urljoin

import oss2
from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage


class OSSFile(File):
  def __init__(self, storage, name, content=None):
    self._storage = storage
    self._name = name
    self._content = content
    self._file = None

  @property
  def name(self):
    return self._name

  def read(self, num_bytes=None):
    if self._content is not None:
      if num_bytes is None:
        return self._content
      return self._content[:num_bytes]
    if self._file is None:
      result = self._storage.bucket.get_object(self._name)
      self._content = result.read()
      self._file = BytesIO(self._content)
    if num_bytes is None:
      return self._file.read()
    return self._file.read(num_bytes)

  def close(self):
    if self._file is not None:
      self._file.close()
      self._file = None


class AliyunOSSStorage(Storage):
  def __init__(self):
    self.access_key_id = settings.OSS_ACCESS_KEY_ID
    self.access_key_secret = settings.OSS_ACCESS_KEY_SECRET
    self.bucket_name = settings.ALIYUN_OSS_BUCKET
    self.endpoint = settings.OSS_ENDPOINT
    self.base_url = settings.OSS_BASE_URL or f'https://{self.bucket_name}.{self.endpoint}'

    auth = oss2.Auth(self.access_key_id, self.access_key_secret)
    self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)

  def _save(self, name, content):
    content.seek(0)
    headers = {}
    content_type = getattr(content, 'content_type', None)
    if not content_type:
      content_type, _ = mimetypes.guess_type(name)
    if content_type:
      headers['Content-Type'] = content_type
    self.bucket.put_object(name, content.read(), headers=headers)
    return name

  def _open(self, name, mode='rb'):
    if 'w' in mode:
      return OSSFile(self, name)
    result = self.bucket.get_object(name)
    return OSSFile(self, name, content=result.read())

  def delete(self, name):
    self.bucket.delete_object(name)

  def exists(self, name):
    return self.bucket.object_exists(name)

  def size(self, name):
    return self.bucket.get_object_meta(name).content_length

  def url(self, name):
    return urljoin(f'{self.base_url}/', name)

  def get_available_name(self, name, max_length=None):
    return super().get_available_name(name, max_length=max_length)
