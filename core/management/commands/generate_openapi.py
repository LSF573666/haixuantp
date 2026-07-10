from django.core.management.base import BaseCommand
from drf_spectacular.generators import SchemaGenerator
import yaml


class Command(BaseCommand):
  help = '生成 OpenAPI YAML 文档到 docs/openapi.yaml'

  def handle(self, *args, **options):
    generator = SchemaGenerator()
    schema = generator.get_schema(request=None, public=True)
    output_path = 'docs/openapi.yaml'
    with open(output_path, 'w', encoding='utf-8') as f:
      yaml.dump(schema, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    self.stdout.write(self.style.SUCCESS(f'OpenAPI 文档已生成: {output_path}'))
