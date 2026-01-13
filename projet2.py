import os
import json
import readchar
import asyncio

class Plateau:
    def __init__(self, taille=20):
        self.taille = taille
        self.taille_totale = taille + 2
        self.grille = [[0 for _ in range(self.taille_totale)] for _ in range(self.taille_totale)]
        
        for i in range(self.taille_totale):
            for j in range(self.taille_totale):
                if i == 0 or i == self.taille_totale - 1 or j == 0 or j == self.taille_totale - 1:
                    self.grille[i][j] = -1
                    
        self.couleurs = {
            -1: "\033[97m██\033[0m", 0: "\033[90m░░\033[0m",
            1: "\033[94m██\033[0m", 2: "\033[93m██\033[0m",
            3: "\033[91m██\033[0m", 4: "\033[92m██\033[0m",
        }

class GestionnairePieces:
    def __init__(self):
        self.formes = {
            "I1": [(0, 0)], "I2": [(0, 0), (0, 1)], "I3": [(0, 0), (0, 1), (0, 2)],
            "V3": [(0, 0), (0, 1), (1, 0)], "I4": [(0, 0), (0, 1), (0, 2), (0, 3)],
            "L4": [(0, 0), (0, 1), (0, 2), (1, 0)], "O4": [(0, 0), (0, 1), (1, 0), (1, 1)],
            "Z4": [(0, 0), (0, 1), (1, 1), (1, 2)], "T4": [(0, 0), (0, 1), (0, 2), (1, 1)],
            "I5": [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)], 
            "X5": [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)],
        }

    def transformer(self, nom, rotation, miroir):
        coords = list(self.formes[nom])
        if miroir:
            coords = [(r, -c) for r, c in coords]
        for _ in range(rotation):
            coords = [(c, -r) for r, c in coords]
        min_r, min_c = min(r for r, _ in coords), min(c for _, c in coords)
        return [(r - min_r, c - min_c) for r, c in coords]

class JeuBlokus:
    def __init__(self):
        self.plateau = Plateau()
        self.gp = GestionnairePieces()
        self.noms_joueurs = ["Bleu", "Jaune", "Rouge", "Vert"]
        self.pieces_joueurs = [{k: True for k in self.gp.formes} for _ in range(4)]
        self.joueur_actuel = 0
        self.premier_coup = [True] * 4
        self.joueurs_bloques = [False] * 4
        self.nb_joueurs_reel = 4
        self.cur_r, self.cur_c = 1, 1
        self.cur_rot, self.cur_mir = 0, 0
        self.p_idx = 0
        self.vainqueur_survie = None
        self.tour_actuel = 1

    def verifier_regles(self, id_p, coords, r_dep, c_dep):
        num_p = id_p + 1
        contact_coin_valide = False
        tous_les_coins = [(1, 1), (1, 20), (20, 20), (20, 1)]
        
        for dr, dc in coords:
            r, c = r_dep + dr, c_dep + dc
            if r < 1 or r > 20 or c < 1 or c > 20 or self.plateau.grille[r][c] != 0:
                return False
            for nr, nc in [(r-1, c), (r+1, c), (r, c-1), (r, c+1)]:
                if self.plateau.grille[nr][nc] == num_p:
                    return False
        
        if self.premier_coup[id_p]:
            for dr, dc in coords:
                if (r_dep + dr, c_dep + dc) in tous_les_coins:
                    contact_coin_valide = True
        else:
            for dr, dc in coords:
                r, c = r_dep + dr, c_dep + dc
                for nr, nc in [(r-1,c-1), (r-1,c+1), (r+1,c-1), (r+1,c+1)]:
                    if self.plateau.grille[nr][nc] == num_p:
                        contact_coin_valide = True
                        
        return contact_coin_valide

    def sauvegarder(self):
        data = {
            "grille": self.plateau.grille,
            "pieces_joueurs": self.pieces_joueurs,
            "joueur_actuel": self.joueur_actuel,
            "premier_coup": self.premier_coup,
            "joueurs_bloques": self.joueurs_bloques,
            "tour_actuel": self.tour_actuel,
            "nb_joueurs_reel": self.nb_joueurs_reel
        }
        with open("sauvegarde_blokus.json", "w") as f:
            json.dump(data, f)
        print("\nPARTIE SAUVEGARDÉE !")

    def charger(self):
        if os.path.exists("sauvegarde_blokus.json"):
            with open("sauvegarde_blokus.json", "r") as f:
                data = json.load(f)
            self.plateau.grille = data["grille"]
            self.pieces_joueurs = data["pieces_joueurs"]
            self.joueur_actuel = data["joueur_actuel"]
            self.premier_coup = data["premier_coup"]
            self.joueurs_bloques = data["joueurs_bloques"]
            self.tour_actuel = data["tour_actuel"]
            self.nb_joueurs_reel = data["nb_joueurs_reel"]
            return True
        return False

    def calculer_scores(self):
        os.system("clear")
        print("\n" + "╔" + "═" * 38 + "╗")
        if self.vainqueur_survie is not None:
            couleur_v = self.plateau.couleurs[self.vainqueur_survie + 1]
            print(f"║ 🏆 GAGNANT : {couleur_v} {self.noms_joueurs[self.vainqueur_survie].upper()} {couleur_v} 🏆 ║")
        else:
            print("║ RÉSULTATS FINAUX ║")
        print("╚" + "═" * 38 + "╝\n")
        
        for i in range(self.nb_joueurs_reel):
            malus = sum(len(self.gp.formes[k]) for k, v in self.pieces_joueurs[i].items() if v)
            print(f" {self.plateau.couleurs[i+1]} Joueur {self.noms_joueurs[i]} : {-malus} pts")

    def afficher_interface(self, forme_coords, nom_p, num_t=1):
        os.system("clear")
        c_act = self.plateau.couleurs[self.joueur_actuel + 1]
        print(f"=== TOUR N°{num_t} | JOUEUR : {c_act} {self.noms_joueurs[self.joueur_actuel].upper()} ===")
        print(f"Pièce: {nom_p} | Flèches: Bouger | R: Rot | M: Mir | Tab: Pièce | S: Sauver | P: Abandon | Enter: Poser")
        print("-" * 60)
        for r in range(self.plateau.taille_totale):
            print(" ", end="")
            for c in range(self.plateau.taille_totale):
                is_prev = any(r == self.cur_r + dr and c == self.cur_c + dc for dr, dc in forme_coords)
                if is_prev:
                    print("\033[97m▒▒\033[0m", end="")
                else:
                    print(self.plateau.couleurs[self.plateau.grille[r][c]], end="")
            print()

    async def client_reseau(self):
        try:
            print("\n--- CONNEXION RÉSEAU ---")
            print("Pour jouer en local (ce PC), appuyez juste sur Entrée.")
            print("Pour rejoindre un autre PC, tapez son IP (ex: 192.168.1.15).")
            
            ip_input = input("IP du serveur : ")
            target_ip = ip_input.strip() if ip_input.strip() else '127.0.0.1'
            
            print(f"Tentative de connexion à {target_ip} sur le port 8888...")
            reader, writer = await asyncio.open_connection(target_ip, 8888)
            
            async def lire_clavier():
                while True:
                    key = await asyncio.get_event_loop().run_in_executor(None, readchar.readkey)
                    cmd = ""
                    if key == readchar.key.UP: cmd = "up"
                    elif key == readchar.key.DOWN: cmd = "down"
                    elif key == readchar.key.LEFT: cmd = "left"
                    elif key == readchar.key.RIGHT: cmd = "right"
                    elif key.lower() == "r": cmd = "r"
                    elif key.lower() == "m": cmd = "m"
                    elif key.lower() == "p": cmd = "p"
                    elif key == readchar.key.TAB: cmd = "tab"
                    elif key in [readchar.key.ENTER, "\r", "\n"]: cmd = "enter"
                    
                    if cmd:
                        writer.write(cmd.encode())
                        await writer.drain()

            asyncio.create_task(lire_clavier())
            
            while True:
                line = await reader.readline()
                if not line: break
                etat = json.loads(line.decode())
                self.joueur_actuel = etat["joueur_actuel"]
                self.cur_r, self.cur_c = etat["cur_r"], etat["cur_c"]
                self.plateau.grille = etat["grille"]
                self.pieces_joueurs = etat["pieces_joueurs"]
                self.tour_actuel = etat.get("num_tour", 1)
                
                if etat["fini"]:
                    self.vainqueur_survie = etat["vainqueur"]
                    self.calculer_scores()
                    break
                    
                self.afficher_interface(etat["forme_piece"], etat["nom_piece"], self.tour_actuel)
        except Exception as e:
            print(f"Erreur de connexion : {e}")
            input("Appuyez sur Entrée pour quitter...")

    def lancer(self):
        os.system("clear")
        print("╔══════════════════════════════════════╗")
        print("║ BLOKUS ULTIMATE ║")
        print("╠══════════════════════════════════════╣")
        print("║ 1. NOUVELLE PARTIE LOCALE ║")
        print("║ 2. REJOINDRE PARTIE RÉSEAU ║")
        print("║ 3. CHARGER DERNIÈRE SAUVEGARDE ║")
        print("╚══════════════════════════════════════╝")
        choix = input("Votre choix : ")

        if choix == "2":
            asyncio.run(self.client_reseau())
            return
            
        if choix == "3" and not self.charger():
            print("Aucune sauvegarde. Mode local activé.")
            choix = "1"
            
        if choix == "1":
            try:
                n = int(input("Nb joueurs (2-4) : "))
            except:
                n = 4
            self.nb_joueurs_reel = n
            for i in range(n, 4):
                self.joueurs_bloques[i] = True

        while not all(self.joueurs_bloques) and self.vainqueur_survie is None:
            if self.joueurs_bloques[self.joueur_actuel]:
                self.joueur_actuel = (self.joueur_actuel + 1) % self.nb_joueurs_reel
                if self.joueur_actuel == 0:
                    self.tour_actuel += 1
                continue
                
            dispos = [k for k, v in self.pieces_joueurs[self.joueur_actuel].items() if v]
            if not dispos:
                self.joueurs_bloques[self.joueur_actuel] = True
                continue

            tour_fini = False
            while not tour_fini:
                nom_p = dispos[self.p_idx % len(dispos)]
                forme = self.gp.transformer(nom_p, self.cur_rot, self.cur_mir)
                self.afficher_interface(forme, nom_p, self.tour_actuel)
                
                key = readchar.readkey()
                if key == readchar.key.UP: self.cur_r = max(1, self.cur_r - 1)
                elif key == readchar.key.DOWN: self.cur_r = min(20, self.cur_r + 1)
                elif key == readchar.key.LEFT: self.cur_c = max(1, self.cur_c - 1)
                elif key == readchar.key.RIGHT: self.cur_c = min(20, self.cur_c + 1)
                elif key.lower() == "r": self.cur_rot = (self.cur_rot + 1) % 4
                elif key.lower() == "m": self.cur_mir = 1 - self.cur_mir
                elif key == readchar.key.TAB: self.p_idx += 1
                elif key.lower() == "s": self.sauvegarder()
                elif key.lower() == "p":
                    self.joueurs_bloques[self.joueur_actuel] = True
                    actifs = [i for i in range(self.nb_joueurs_reel) if not self.joueurs_bloques[i]]
                    if len(actifs) <= 1:
                        if len(actifs) == 1:
                            self.vainqueur_survie = actifs[0]
                        tour_fini = True
                    tour_fini = True
                elif key in [readchar.key.ENTER, "\r", "\n"]:
                    if self.verifier_regles(self.joueur_actuel, forme, self.cur_r, self.cur_c):
                        for dr, dc in forme:
                            self.plateau.grille[self.cur_r+dr][self.cur_c+dc] = self.joueur_actuel+1
                        self.pieces_joueurs[self.joueur_actuel][nom_p] = False
                        self.premier_coup[self.joueur_actuel] = False
                        tour_fini = True

            self.joueur_actuel = (self.joueur_actuel + 1) % self.nb_joueurs_reel
            if self.joueur_actuel == 0:
                self.tour_actuel += 1

        self.calculer_scores()

if __name__ == "__main__":
    JeuBlokus().lancer()