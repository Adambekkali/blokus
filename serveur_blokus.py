import asyncio
import json
import socket
from projet2 import JeuBlokus

class ServeurBlokus:
    def __init__(self):
        self.jeu = JeuBlokus()
        self.clients = []
        self.nombre_tours = 1
        self.jeu_lance = False

    async def diffuser_etat(self):
        self.jeu.nb_joueurs_reel = len(self.clients)
        dispos = [k for k, v in self.jeu.pieces_joueurs[self.jeu.joueur_actuel].items() if v]
        nom_p = dispos[self.jeu.p_idx % len(dispos)] if dispos else "Fin"
        forme = self.jeu.gp.transformer(nom_p, self.jeu.cur_rot, self.jeu.cur_mir) if dispos else []

        etat = {
            "grille": self.jeu.plateau.grille,
            "joueur_actuel": self.jeu.joueur_actuel,
            "nom_piece": nom_p,
            "forme_piece": forme,
            "pieces_joueurs": self.jeu.pieces_joueurs,
            "cur_r": self.jeu.cur_r,
            "cur_c": self.jeu.cur_c,
            "num_tour": self.nombre_tours,
            "fini": (self.jeu.vainqueur_survie is not None) or all(self.jeu.joueurs_bloques[:len(self.clients)]),
            "vainqueur": self.jeu.vainqueur_survie
        }
        
        message = (json.dumps(etat) + "\n").encode()
        for _, writer in self.clients:
            try:
                writer.write(message)
                await writer.drain()
            except:
                pass

    async def handle_client(self, reader, writer):
        if self.jeu_lance or len(self.clients) >= 4:
            writer.close()
            return
            
        my_id = len(self.clients)
        self.clients.append((reader, writer))
        print(f"Joueur {my_id} ({self.jeu.noms_joueurs[my_id]}) connecté.")
        
        if len(self.clients) == 2:
            print("2 joueurs connectés. Lancement dans 10 secondes (attente d'autres joueurs...)")
            await asyncio.sleep(10)
            self.jeu_lance = True
            await self.diffuser_etat()
        elif len(self.clients) > 2:
            if self.jeu_lance:
                await self.diffuser_etat()

        while True:
            try:
                data = await reader.read(1024)
                if not data:
                    break
                
                if my_id == self.jeu.joueur_actuel:
                    self.appliquer_logique(data.decode())
                    await self.diffuser_etat()
            except:
                break
        writer.close()

    def appliquer_logique(self, touche):
        j = self.jeu
        nb = len(self.clients)
        
        if touche == "up": j.cur_r = max(1, j.cur_r - 1)
        elif touche == "down": j.cur_r = min(20, j.cur_r + 1)
        elif touche == "left": j.cur_c = max(1, j.cur_c - 1)
        elif touche == "right": j.cur_c = min(20, j.cur_c + 1)
        elif touche == "r": j.cur_rot = (j.cur_rot + 1) % 4
        elif touche == "m": j.cur_mir = 1 - j.cur_mir
        elif touche == "tab": j.p_idx += 1
        elif touche == "p":
            j.joueurs_bloques[j.joueur_actuel] = True
            actifs = [i for i in range(nb) if not j.joueurs_bloques[i]]
            if len(actifs) == 1:
                j.vainqueur_survie = actifs[0]
            elif len(actifs) == 0:
                pass 
            else:
                j.joueur_actuel = actifs[0]
        elif touche == "enter":
            dispos = [k for k, v in j.pieces_joueurs[j.joueur_actuel].items() if v]
            if dispos:
                nom_p = dispos[j.p_idx % len(dispos)]
                forme = j.gp.transformer(nom_p, j.cur_rot, j.cur_mir)
                
                if j.verifier_regles(j.joueur_actuel, forme, j.cur_r, j.cur_c):
                    for dr, dc in forme:
                        j.plateau.grille[j.cur_r+dr][j.cur_c+dc] = j.joueur_actuel+1
                    j.pieces_joueurs[j.joueur_actuel][nom_p] = False
                    j.premier_coup[j.joueur_actuel] = False
                    
                    for _ in range(nb):
                        j.joueur_actuel = (j.joueur_actuel + 1) % nb
                        if not j.joueurs_bloques[j.joueur_actuel]:
                            break
                    
                    if j.joueur_actuel == 0:
                        self.nombre_tours += 1

def trouver_meilleure_ip():
    """Tente de trouver l'IP du réseau local (Wi-Fi)"""
    liste_ips = []
    
    # Méthode 1 : Via le nom d'hôte (Spécial Mac : ajout de .local)
    try:
        hostname = socket.gethostname()
        if not hostname.endswith(".local"):
            hostname += ".local"
        ips = socket.gethostbyname_ex(hostname)[2]
        liste_ips.extend(ips)
    except:
        pass

    # Méthode 2 : Connexion UDP factice (Fallback)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 1))
        liste_ips.append(s.getsockname()[0])
        s.close()
    except:
        pass

    # Filtrage : On cherche en priorité 192.168.x.x
    ip_finale = "127.0.0.1"
    
    # On enlève les doublons
    liste_ips = list(set(liste_ips))
    
    # 1. Priorité absolue aux 192.168...
    for ip in liste_ips:
        if ip.startswith("192.168."):
            return ip
            
    # 2. Sinon une IP en 10... ou 172... (mais pas 100.)
    for ip in liste_ips:
        if (ip.startswith("10.") and not ip.startswith("100.")) or ip.startswith("172."):
            return ip
            
    # 3. Sinon on prend la première qui n'est pas localhost
    for ip in liste_ips:
        if not ip.startswith("127.") and not ip.startswith("100."):
            return ip
            
    return ip_finale

async def main():
    srv = ServeurBlokus()
    
    # Détection automatique de la bonne IP
    IP = trouver_meilleure_ip()

    # On écoute sur 0.0.0.0
    server = await asyncio.start_server(srv.handle_client, '0.0.0.0', 8888)
    
    print("==================================================")
    print(f"SERVEUR BLOKUS DÉMARRÉ")
    print(f"✅ IP À DONNER AUX JOUEURS : {IP}")
    print(f"(Si ça échoue, essayez les autres IPs trouvées)")
    print("==================================================")
    
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())