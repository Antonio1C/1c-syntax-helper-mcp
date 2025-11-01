"""
Константы проекта.
"""

# Elasticsearch настройки
ELASTICSEARCH_DEFAULT_HOST = "localhost"
ELASTICSEARCH_DEFAULT_PORT = 9200
ELASTICSEARCH_INDEX_NAME = "help1c_docs"
ELASTICSEARCH_CONNECTION_TIMEOUT = 30
ELASTICSEARCH_REQUEST_TIMEOUT = 60

# Парсинг
BATCH_SIZE = 100  # Размер батча для парсинга HBK файлов
MAX_FILE_SIZE_MB = 50
SUPPORTED_ENCODINGS = ["utf-8", "cp1251", "iso-8859-1"]

# Логирование
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Rate limiting
REQUESTS_PER_MINUTE = 60
REQUESTS_PER_HOUR = 1000

# Поиск
MAX_SEARCH_RESULTS = 100
SEARCH_TIMEOUT_SECONDS = 30
MIN_SCORE_THRESHOLD = 0.1

# Файловые операции
TEMP_DIR_PREFIX = "help1c_temp_"
EXTRACTION_TIMEOUT_SECONDS = 300

# HTTP
DEFAULT_REQUEST_TIMEOUT = 30
MAX_REQUEST_SIZE_MB = 10
