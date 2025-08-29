# MySQL Database Configuration via environment variables (fallbacks for local dev)
import os

MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'milgiros.vpshost10156.mysql.dbaas.com.br'),
    'database': os.environ.get('MYSQL_DATABASE', 'milgiros'),
    'user': os.environ.get('MYSQL_USER', 'milgiros'),
    'password': os.environ.get('MYSQL_PASSWORD', 'Aa1234567890@@'),
    'charset': os.environ.get('MYSQL_CHARSET', 'utf8mb4'),
    'autocommit': True,
}
