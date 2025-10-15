import pymysql
from config import *
from logger import log

def db_connect():
    """Establish MySQL connection."""
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME
    )

def get_connections_in_range():
    """Return list of (username, ip) tuples for Guacamole connections within IP range."""
    try:
        conn = db_connect()
        cur = conn.cursor(pymysql.cursors.DictCursor)

        query = """
            SELECT
                c.connection_name AS username,
                MAX(CASE WHEN p.parameter_name = 'hostname' THEN p.parameter_value END) AS hostname
            FROM guacamole_connection c
            LEFT JOIN guacamole_connection_parameter p
                ON c.connection_id = p.connection_id
            GROUP BY c.connection_id, c.connection_name;
        """

        cur.execute(query)
        rows = cur.fetchall()
        conn.close()

        results = []
        for row in rows:
            ip = row["hostname"]
            user = row["username"]
            if not ip:
                continue
            if ip.startswith(IP_PREFIX):
                try:
                    last_octet = int(ip.split(".")[-1])
                    if IP_RANGE_START <= last_octet <= IP_RANGE_END:
                        results.append((user, ip))
                except ValueError:
                    continue

        return results

    except Exception as e:
        log(f"[!] Database query failed: {e}")
        return []
