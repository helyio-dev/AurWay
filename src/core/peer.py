import socket
import select 
import sys
import threading
import time
import os
import base64
import subprocess
import requests 
import atexit 
import socks as pysocks 

from cryptography.fernet import Fernet 
from stem.util import term 


SECRET_KEY = b'Yflg4g0AUDHAWzuWkM84tWzPh85dNU9FqrIFIjd9J1QvBWmPLIScwdgWFn65T9JDKWbuKfCduhiXg0MEdZ1QJ5EOIxsceySxraDTL1IHksS7CQvTSjYDG9EVvUivKfo1'
CONNECTIONS = {}
PEER_IDENTIFIERS = {} 
ID_COUNTER = 0 
ID_LOCK = threading.Lock() 

TOR_CONTROL_PORT = 9051
TOR_SOCKS_PORT = 9050 

KNOWN_PEERS_URL = "https://raw.githubusercontent.com/lmms/lmms/main/peers.txt" 

class PeerCrypter:
    def __init__(self, key):
        self.cipher_suite = Fernet(base64.urlsafe_b64encode(key[:32])) 

    def encrypt_message(self, message):
        return self.cipher_suite.encrypt(message.encode('utf-8'))

    def decrypt_message(self, token):
        try:
            return self.cipher_suite.decrypt(token).decode('utf-8')
        except Exception:
            return None 

PEER_CRYPTER = PeerCrypter(SECRET_KEY)

def handle_incoming_data(s, inputs, server_socket):
    global CONNECTIONS, PEER_IDENTIFIERS
    try:
        data = s.recv(1024)
        if data:
            decrypted_message = PEER_CRYPTER.decrypt_message(data)
            
            if decrypted_message is None:
                print(f"\n[!] Message illisible (chiffrement) reçu de {s.getpeername()}")
                return

            message = decrypted_message.strip()
            
            peer_id_display = PEER_IDENTIFIERS.get(s, s.getpeername()[1]) 
            
            print(f"\n[*] Message reçu de {peer_id_display} : {message}")
            
            for other_peer in inputs:
                if other_peer is not server_socket and other_peer is not s:
                    try:
                        other_peer.send(data) 
                    except:
                        other_peer.close()
                        if other_peer in inputs: inputs.remove(other_peer)
                        if other_peer in CONNECTIONS: del CONNECTIONS[other_peer]
                        if other_peer in PEER_IDENTIFIERS: del PEER_IDENTIFIERS[other_peer]
        else:
            closed_peer_id = PEER_IDENTIFIERS.get(s, s.getpeername())
            print(f"\n[-] Connexion fermée par {closed_peer_id}")
            
            if s in inputs: inputs.remove(s)
            s.close()
            if s in CONNECTIONS: del CONNECTIONS[s]
            if s in PEER_IDENTIFIERS: del PEER_IDENTIFIERS[s]

    except Exception as e:
        error_peer_id = PEER_IDENTIFIERS.get(s, s.getpeername())
        print(f"\n[!] Erreur de communication avec {error_peer_id}: {e}")
        
        if s in inputs: inputs.remove(s)
        s.close()
        if s in CONNECTIONS: del CONNECTIONS[s]
        if s in PEER_IDENTIFIERS: del PEER_IDENTIFIERS[s]

def initiate_connection(target_ip, target_port, inputs):
    client_socket = pysocks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        client_socket.set_proxy(pysocks.SOCKS5, '127.0.0.1', TOR_SOCKS_PORT)
        
        client_socket.connect((target_ip, target_port))
        
        with ID_LOCK:
            global ID_COUNTER 
            ID_COUNTER += 1
            PEER_IDENTIFIERS[client_socket] = f"Peer #{ID_COUNTER}"
        
        print(f"[*] Connexion active réussie (via Tor) à {target_ip}:{target_port}. Identifiant local: {PEER_IDENTIFIERS[client_socket]}")
        
        inputs.append(client_socket) 
        send_thread = threading.Thread(target=send_data_thread, args=(client_socket,), daemon=True)
        send_thread.start()
        
    except pysocks.ProxyConnectionError:
        print(f"[!!!] FATAL: Impossible de se connecter via Tor. Assurez-vous que le client Tor est démarré.")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Erreur de connexion initiale (via Tor) : {e}")

def send_data_thread(conn):
    try:
        while True:
            message = input() 
            
            if message.lower() == 'exit':
                conn.close()
                os._exit(0)
            
            if message:
                encrypted_message = PEER_CRYPTER.encrypt_message(message)
                conn.sendall(encrypted_message)

    except EOFError:
        conn.close()
        os._exit(0)
    except Exception:
        conn.close()
        os._exit(0)

def discover_peers(inputs):
    proxies = {
        'http': f'socks5h://127.0.0.1:{TOR_SOCKS_PORT}',
        'https': f'socks5h://127.0.0.1:{TOR_SOCKS_PORT}'
    }
    print(f"[*] Tentative de découverte de peers depuis l'annuaire (via Tor)...")
    try:
        response = requests.get(KNOWN_PEERS_URL, proxies=proxies, timeout=5)
        response.raise_for_status() 
        peer_list = [line.strip() for line in response.text.split('\n') if line.strip() and line.endswith(f':{os.path.basename(os.getcwd()).split("-")[-1]}')]
        if peer_list:
            print(f"[+] Peers trouvés : {len(peer_list)}. Essai de connexion au(x) premier(s)...")
            for peer_addr in peer_list[:2]:
                try:
                    ip, port = peer_addr.split(':')
                    port = int(port)
                    threading.Thread(target=initiate_connection, args=(ip, port, inputs), daemon=True).start()
                except:
                    continue
        else:
            print("[*] Annuaire de peers trouvé, mais la liste est vide.")
            return []
    except requests.exceptions.Timeout:
        print("[!] La requête de découverte a expiré (Tor est peut-être lent).")
    except requests.exceptions.RequestException as e:
        print(f"[!] Erreur de découverte de peers : {e}. Continue sans connexion automatique.")
    return []

def find_tor_executable():
    project_path = os.path.join(os.getcwd(), 'tor', 'tor.exe')
    if os.path.exists(project_path):
        return project_path
    return None

def start_tor_service(local_port, target_address=None):
    
    tor_exe = find_tor_executable()
    if not tor_exe:
        print(f"[!!!] FATAL: tor.exe est introuvable. Placez le binaire Tor dans le dossier 'tor/'.")
        sys.exit(1)

    print(f"[*] tor.exe trouvé à : {tor_exe}")
    print(f"[*] Démarrage du client Tor et configuration du service caché (port {local_port})...")
    
    tor_process = None
    onion_address = None

    try:
        tor_data_dir = os.path.join(os.getcwd(), 'tor', 'data')
        tor_hs_dir = os.path.join(tor_data_dir, 'hidden_service')
        os.makedirs(tor_hs_dir, exist_ok=True)
        
        torrc_path = os.path.join(tor_data_dir, 'torrc')
        torrc_content = f"""
SocksPort {TOR_SOCKS_PORT}
ControlPort {TOR_CONTROL_PORT}
DataDirectory {tor_data_dir}
HiddenServiceDir {tor_hs_dir}
HiddenServicePort {local_port} 127.0.0.1:{local_port}
ExitPolicy reject *:*
"""
        with open(torrc_path, 'w') as f:
            f.write(torrc_content.strip())
            
        command_args = [tor_exe, '-f', torrc_path]
        
        tor_process = subprocess.Popen(command_args,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        
        def cleanup_tor():
            if tor_process and tor_process.poll() is None:
                tor_process.kill()
        atexit.register(cleanup_tor)

        onion_file = os.path.join(tor_hs_dir, 'hostname')
        max_wait = 30
        print(term.format("[*] En attente de la création de l'adresse .onion...", term.Color.BLUE))
        while not os.path.exists(onion_file) and max_wait > 0:
            time.sleep(1)
            max_wait -= 1

        if not os.path.exists(onion_file):
            raise Exception("Le service Tor n'a pas réussi à créer l'adresse .onion dans le temps imparti. Vérifiez les logs.")

        with open(onion_file, 'r') as f:
            onion_address = f.read().strip()

        print(f"\n[+] Peer anonyme prêt. Adresse .onion: {onion_address}:{local_port}")
        
        start_p2p_loop(local_port, target_address, onion_address)

    except Exception as e:
        print(f"[!!!] FATAL: Erreur critique lors du démarrage de Tor. {e}")
        if tor_process and tor_process.poll() is None:
             print(f"Erreur du processus Tor : {tor_process.stderr.read().decode()}")
        sys.exit(1)
    finally:
        pass


def start_p2p_loop(local_port, target_address, onion_address):
    global CONNECTIONS, PEER_IDENTIFIERS, ID_COUNTER
    inputs = [] 
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.setblocking(0)
    
    try:
        server_socket.bind(('127.0.0.1', local_port)) 
    except socket.error as e:
        print(f"[!] Erreur: Le port {local_port} est déjà utilisé localement. {e}")
        return
        
    server_socket.listen(5)
    inputs.append(server_socket)
    
    if not target_address:
        discover_peers(inputs) 
        
    if target_address:
        try:
            target_ip, target_port_str = target_address.split(':')
            target_port = int(target_port_str)
            
            conn_thread = threading.Thread(target=initiate_connection, 
                                           args=(target_ip, target_port, inputs), 
                                           daemon=True)
            conn_thread.start()
            
        except ValueError:
            print(f"[!] Format de cible invalide : {target_address}. Utiliser IP:PORT ou ONION:PORT.")
        except Exception as e:
            print(f"[!] Erreur de connexion initiale : {e}")

    try:
        while inputs:
            readable, _, exceptional = select.select(inputs, [], inputs, 1)
            
            for s in readable:
                if s is server_socket:
                    connection, client_address = s.accept()
                    connection.setblocking(0)
                    inputs.append(connection)
                    CONNECTIONS[connection] = client_address
                    
                    with ID_LOCK:
                        ID_COUNTER += 1
                        PEER_IDENTIFIERS[connection] = f"Peer #{ID_COUNTER}"
                    
                    print(f"\n[+] Nouvelle connexion reçue (via Tor). Identifiant local: {PEER_IDENTIFIERS[connection]}")
                    
                    send_thread = threading.Thread(target=send_data_thread, args=(connection,), daemon=True)
                    send_thread.start()
                    
                else:
                    handle_incoming_data(s, inputs, server_socket)

            for s in exceptional:
                pass 

    except KeyboardInterrupt:
        print("\n[!] Arrêt du peer par l'utilisateur.")
    except Exception as e:
        print(f"\n[!] Erreur inattendue dans la boucle principale : {e}")
        
    for s in inputs:
        s.close()
    
    os._exit(0)


def start_peer(local_port, target_address=None):
    start_tor_service(local_port, target_address)