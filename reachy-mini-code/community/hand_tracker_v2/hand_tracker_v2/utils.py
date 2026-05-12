import copy
import math
import numpy as np

def finger_orientation_deg(mcp, tip):
    """
    Calcule l'angle d'orientation d'un doigt basé sur MCP et TIP.
    
    mcp : (x, y)
    tip : (x, y)
    
    Retour :
        angle en degrés, 0 = doigt vertical vers le haut
        positif = vers la droite
        négatif = vers la gauche
    """

    # Vecteur MCP → TIP
    v = np.array([tip[0] - mcp[0], tip[1] - mcp[1]])

    # Comme l'image est inversée verticalement en coordonnées (y augmente vers le bas)
    # on inverse l'axe Y pour un repère standard
    v[1] = -v[1]

    # Calcul de l'angle du vecteur
    angle = math.degrees(math.atan2(v[0], v[1]))

    # angle = 0 quand vertical, positive vers la droite
    return angle

def angle_diff(a: float, b: float) -> float:
    """Returns the smallest distance between 2 angles"""
    d = a - b
    d = ((d + math.pi) % (2 * math.pi)) - math.pi
    return d


def allow_multiturn(new_joints: list[float], prev_joints: list[float], max_delta: float) -> list[float]:
    """This function will always guarantee that the joint takes the shortest path to the new position.
    The practical effect is that it will allow the joint to rotate more than 2pi if it is the shortest path.
    """
    new_joints = copy.deepcopy(new_joints)
    for i in range(len(new_joints)):
        diff = angle_diff(new_joints[i], prev_joints[i])
        if abs(diff) > max_delta:
            if diff > 0:
                diff = max_delta
            else:
                diff = -max_delta
        new_joints[i] = prev_joints[i] + diff
        if new_joints[i] > 3* math.pi:
            new_joints[i] -= 2*math.pi
        elif new_joints[i] < -3* math.pi:
            new_joints[i] += 2*math.pi
    return new_joints