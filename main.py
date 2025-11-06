import sys
from src.core.peer import start_peer

def main():
    if len(sys.argv) < 2:
        print("Usage : python main.py <port_local> [cible_onion:port_cible]")
        print("\nExemples de lancement (Peer A) :")
        print("  python main.py 6000")
        print("    -> Peer A écoute de manière anonyme. Il affichera son adresse .onion.")
        print("\nExemples de connexion (Peer B) :")
        print("  python main.py 6001 abcdef12345678.onion:6000")
        print("    -> Peer B écoute sur 6001 ET se connecte à Peer A via son adresse .onion.")
        sys.exit(1)

    try:
         local_port = int(sys.argv[1])
    except ValueError:
        print("Erreur : Le port local doit être un nombre valide.")
        sys.exit(1)

    target_address = sys.argv[2] if len(sys.argv) > 2 else None
    
    start_peer(local_port, target_address) 

if __name__ == "__main__":
    main()