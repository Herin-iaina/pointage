import time
from zk import ZK
from .utils import parse_user_raw

# Configuration par défaut
MACHINE_PORT = 4370
CAPTURE_SLEEP = 1

class ZKClient:
    def __init__(self, machine_ips, port=MACHINE_PORT, timeout=15):
        self.machine_ips = machine_ips
        self.port = port
        self.timeout = timeout

    def fetch_users_from_machine(self, machine_ip):
        """Récupère les utilisateurs depuis un appareil ZK."""
        results = []
        
        zk = ZK(machine_ip, port=self.port, timeout=self.timeout, password=0, force_udp=False, ommit_ping=True, encoding='ISO-8859-1')
        conn = None
        try:
            conn = zk.connect()
            users_list = conn.get_users()

            for user in users_list:
                user_id = getattr(user, 'user_id', None)
                name = getattr(user, 'name', '') or ''
                privilege = getattr(user, 'privilege', None)
                group_id = getattr(user, 'group_id', None)
                card_number = getattr(user, 'card_number', None)
                title = getattr(user, 'title', None) or getattr(user, 'title_name', None)
                number = getattr(user, 'number', None) or getattr(user, 'no', None) or getattr(user, 'user_no', None)

                raw_str = str(user)
                if (not title or not number) and raw_str:
                    parsed = parse_user_raw(raw_str)
                    if not title:
                        title = parsed.get('title')
                    if not number:
                        number = parsed.get('number') or parsed.get('card_number')

                results.append({
                    'device_ip': machine_ip,
                    'user_id': user_id,
                    'name': name,
                    'title': title,
                    'number': number,
                    'privilege': privilege,
                    'group_id': group_id,
                    'card_number': card_number,
                    'raw': raw_str
                })

        except Exception as e:
            print(f"  ✗ Erreur {machine_ip}: {e}")
        finally:
            try:
                if zk is not None:
                    zk.disconnect()
            except Exception:
                try:
                    if conn:
                        conn.disconnect()
                except Exception:
                    pass

        return results

    def fetch_attendance_from_machine(self, machine_ip):
        """Récupère les enregistrements d'attendance depuis un appareil ZK."""
        results = []
        
        zk = ZK(machine_ip, port=self.port, timeout=self.timeout, password=0, force_udp=False, ommit_ping=True, encoding='ISO-8859-1')
        conn = None
        try:
            conn = zk.connect()
            attendance_list = conn.get_attendance()

            for entry in attendance_list:
                user_id = getattr(entry, 'user_id', None) or getattr(entry, 'user', None)
                ts = getattr(entry, 'timestamp', None) or getattr(entry, 'time', None)
                status = getattr(entry, 'status', None)
                punch_state = getattr(entry, 'punch_state', None)
                
                results.append({
                    'device_ip': machine_ip,
                    'raw': str(entry),
                    'user_id': user_id,
                    'timestamp': ts,
                    'status': status,
                    'punch_state': punch_state
                })

        except Exception as e:
            print(f"  ✗ Erreur {machine_ip}: {e}")
        finally:
            try:
                if zk is not None:
                    zk.disconnect()
            except Exception:
                try:
                    if conn:
                        conn.disconnect()
                except Exception:
                    pass

        return results

    def collect_all_users(self):
        """Collecte les utilisateurs depuis toutes les machines."""
        all_users = []
        for ip in self.machine_ips:
            print(f"  → {ip}...", end=' ', flush=True)
            users = self.fetch_users_from_machine(ip)
            print(f"✓ ({len(users)} users)")
            all_users.extend(users)
            time.sleep(CAPTURE_SLEEP)
        return all_users

    def collect_all_attendance(self):
        """Collecte les enregistrements d'attendance depuis toutes les machines."""
        all_data = []
        for ip in self.machine_ips:
            print(f"  → {ip}...", end=' ', flush=True)
            data = self.fetch_attendance_from_machine(ip)
            print(f"✓ ({len(data)} records)")
            all_data.extend(data)
            time.sleep(CAPTURE_SLEEP)
        return all_data
