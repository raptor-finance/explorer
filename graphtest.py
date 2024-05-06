class ErrProfondeur(Exception):
    pass

class ErrTeleportation(Exception):
    pass

class Arc(object):
    def __init__(self, src, dest, cout):
        self.src = src
        self.dest = dest
        self.cout = cout

    def refresh(self):
        pass # existe: peut etre modifie en heritant

    def __getitem__(self, i):
        if i == 0:
            return self.src
        elif i == 1:
            return self.dest
        elif i == 2:
            return self.cout
        else:
            raise IndexError("Vous semblez egare, cher voyageur?")

class Route(object):
    # bah oui un chemin mais en mieux
    cout = 0
    
    arcs = []
    noeuds = []
    lCouts = []
    src = None
    dest = None
    
    def __init__(self,*,arcs=None, autreRoute=None):
        if arcs:
            self.src = arcs[0][0]
            self.noeuds = [self.src]
            self.ajouteArcs(self, arcs)
        elif autreRoute: # pour les copies
            self.src = autreRoute.src
            self.dest = autreRoute.dest
            self.cout = autreRoute.cout
            self.arcs = autreRoute.arcs
            
            self.noeuds = autreRoute.noeuds.copy()
            self.lCouts = autreRoute.lCouts.copy()

    def __len__(self):
        return len(self.noeuds)

    def __repr__(self):
        return f"Route({self.noeuds})"

    def eviteTeleportation(self, arc):
        if not len(self.noeuds):
            self.noeuds = [arc[0]]
        if arc[0] != self.noeuds[-1]:
            # on pardonne pas ici (sinon on casse tout)
            raise ErrTeleportation(f"Teleportation detectee: {arc[0]} != {self.noeuds[-1]}")

    def ajouteArcs(self, arcs):
        for arc in arcs:
            self.eviteTeleportation(arc)
            self.noeuds.append(arc[1])
            self.lCouts.append(arc[2])
            self.cout += arc[2]
            
        self.arcs = self.arcs + arcs
        self.dest = self.noeuds[-1]

    def append(self, arc):
        # vous vous voyez vraiment ajouter les petits crochets a chaque fois? (en + c'est moche)
        # en plus ca marche comme le append donc pourquoi pas
        self.ajouteArcs([arc])

    def marcheArriere(self, profondeur):
        if len(self.noeuds) < profondeur:
            raise ErrProfondeur(f"Trop profond, chef!")
        for i in range(profondeur):
            coutEtape = self.lCouts.pop()
            self.noeuds.pop()
            self.cout -= coutEtape
        self.dest = self.noeuds[-1]
        
    def copy(self):
        return Route(autreRoute=self)

    def updateCout(self):
        self.cout = sum([a[2] for a in self.arcs])

    def __add__(self, b):
        assert(type(b) == type(self))
        if self.dest != b.src:
            raise ErrTeleportation("Ajout impossible: pas de jonction entre les chemins (sauf teleportation)")
        n = self.copy()
        # ressemble a une somme de vecteurs
        n.noeuds = self.noeuds + b.noeuds
        n.couts = self.couts + b.couts
        
        n.cout = self.cout + b.cout
        n.src = self.src
        n.dest = b.dest
        
        n.arcs = self.arcs + b.arcs
        
        return n

    def __iadd__(self, b):
        assert(type(b) == type(self))
        if self.dest != b.src:
            raise ErrTeleportation("Ajout impossible: pas de jonction entre les chemins (sauf teleportation)")
        self.noeuds += b.noeuds
        self.couts += b.couts
        n.arcs = self.arcs + b.arcs
        self.dest = b.dest

class NullRoute(Route):
    # bah oui comme le vecteur nul
    def __init__(self, depart=None):
        self.cout = 0
        self.src = depart
        self.dest=depart
        
        self.noeuds=[depart] if depart else []
        self.lCouts = []

class Sommet(object):
    def __init__(self, name, *, _dests=None):
        self.arcs = []
        self.name = name
        self.dests = _dests if _dests else []
        
        self.couts = []
    
    def ajouteDest(self, dest):
        if dest[0] != self:
            return # on pardonne pour ca
        if dest[1] in self.dests:
            return
        self.dests.append(dest[1])
        self.arcs.append(dest)
        
    def accessiblesEn(self, hops):
        # sponsorise par le lobby des patissiers fabricants de mille-feuilles
        coucheActuelle = [self]
        for i in range(hops):
            _nHops = []
            for noeud in coucheActuelle:
                _nHops = _nHops + noeud.dests
            coucheActuelle = _nHops
        return coucheActuelle

    def accessibleJusquA(self, hops):
        coucheActuelle = [self]
        
        tout = [(coucheActuelle.copy(), 0)] # oui flemme de re-ecrire [self]
        for i in range(hops):
            _nHops = []
            for noeud in coucheActuelle:
                _nHops += noeud.dests
            coucheActuelle = _nHops
            tout.append((_nHops.copy(), i+1))
        return tout

    def cheminPlusCourt(self, nomCherche, maxK):
        """
            Renvoie le chemin le plus court sans se soucier de son coût
        """
    
    
        stack = [NullRoute(self)]
        
        for k in range(maxK):
            nStack = []
            for element in stack:
                for arc in element.dest.arcs:
                    if (arc[0] == arc[1]) or (arc[1] in element.noeuds):
                        continue
                    # print(element.dest.arcs)
                    S = element.copy()
                    S.append(arc)
                    if S.dest.name == nomCherche:
                        return S
                    nStack.append(S)
            stack = nStack

    def tousLesChemins(self, destination, maxK):
        stack = [NullRoute(self)]
        cheminsValides = []
        
        for k in range(maxK):
            nStack = []
            for element in stack:
                for arc in element.dest.arcs:
                    # vire les boucles
                    if ((arc[0] == arc[1]) or (arc[1] in element.noeuds)) and arc[1] != element.noeuds[0]:
                        continue
                    S = element.copy()
                    S.append(arc)
                    if S.dest.name == destination:
                        cheminsValides.append(S)
                    else:   # destination atteinte, pas la peine d'explorer plus loin
                        nStack.append(S)
            stack = nStack
        return cheminsValides

    def cheminMoinsCher(self, destination, maxK):
        """
            Renvoie le chemin le moins cher, peu importe sa longueur.
            Long car il cherche tous les chemins possibles!
        """
        cheminsValides = self.tousLesChemins(destination, maxK)
        return min(cheminsValides, key=lambda c: c.cout) if len(cheminsValides) else None

    def __repr__(self):
        return self.name

graph = {}

def creeSommet(nom, classeCustom=Sommet):
    if not graph.get(nom):
        graph[nom] = classeCustom(nom)

def ajouteArc(arc):
    arc[0].ajouteDest(arc)

sommets = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i']

arcs = [('a', 'b', 1),
        ('b', 'c', 3),
        ('c', 'd', 5),
        ('b', 'd', 3.14),
        ('d', 'b', 6),
        ('d', 'e', 2**0.5),
        ('b', 'b', 1),
        
        ('a', 'f', 0),
        ('f', 'g', 0),
        ('g', 'h', 0),
        ('h', 'i', 0),
        ('i', 'e', 0)
        # ('a', 'e', 50)
        ]
      

def setupSommets(mesSommets):
    for nSommet in mesSommets:
        creeSommet(nSommet)
    
def setupArcs(mesArcs):
    for arc in mesArcs:
        # les noms c'est mignon mais les objets c'est plus pratique
        arcObj = Arc(graph[arc[0]], graph[arc[1]], arc[2])
        ajouteArc(arcObj)

def tousLesChemins(a,b):
    return graph[a].tousLesChemins(b, len(graph.keys()))

def plusCourtChemin(a, b):
    return graph[a].cheminPlusCourt(b, len(graph.keys()))

def cheminLeMoinsCher(a, b):
    return graph[a].cheminMoinsCher(b, len(graph.keys()))

if __name__ == "__main__":
    setupSommets(sommets)
    setupArcs(arcs)

    c = graph["a"].cheminPlusCourt("e", len(graph.keys()))
    g = graph["a"].cheminMoinsCher("e", len(graph.keys()))
    print("Chemin le plus court de a vers e (sans tenir compte du cout):", c.noeuds, 'longueur:',  len(c.noeuds), 'cout:', c.cout)
    print("Chemin le moins cher de a vers e (en ignorant la longueur):", g.noeuds, 'longueur:', len(g.noeuds), 'cout:', g.cout)

    print("")

    print("Tous les chemins entre a et e (boucles exclues):", graph["a"].tousLesChemins("e", len(graph.keys())))