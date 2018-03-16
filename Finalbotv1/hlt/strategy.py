import logging
import math
import random

import hlt

def first_turn(gmap, gstate):
    '''
    Assign first commands to starting ships
    '''

    #Assess planets
    gstate.assess_planets()

    #get init ships
    ships = gmap.get_me().all_ships()
    gstate.ships_init = [s.id for s in ships]

    #find closest oponent and their respective distance
    if gstate.n_players > 2:
        closest_player = gmap.get_player((gmap.get_me().id + 2)%4)
    else:
        closest_player = gmap.get_player((gmap.get_me().id + 1)%2)
    enems = closest_player.all_ships()
    min_ship = min(ships, key=lambda s: abs(s.y - gmap.height/2))
    min_enem = min(enems, key=lambda e: abs(e.y - gmap.height/2))
    min_dist = min_ship.calculate_distance_between(min_enem)

    # 2 player games
    if gstate.n_players == 2:
        #If enemy spawns within 15*max_speed units, go all in
        if min_dist < 15*hlt.constants.MAX_SPEED:
            logging.info('Strategic: Executing All-In opening')
            gstate.add_squadron(closest_player.id, gstate.all_ships)
        else:
            logging.info('Strategic: Executing Early Scaling opening')
            p = 0
            ships = [gmap.get_me().get_ship(sid) for sid in gstate.all_ships]
            ships.sort(key=hlt.entity.Position(gmap.width/2, gmap.height/2).calculate_distance_between)
            gstate.all_ships = [ship.id for ship in ships]
            for ship_id in gstate.all_ships:
                if gstate.get_ship_role(ship_id) != 1:
                    gstate.set_ship_role(ship_id, 1)
                    gstate.ships_mine.append(ship_id)
                
                if not p:
                    p = queue_planets(gmap, gstate, ship_id)
                elif len(gstate.plan_miners[p.id]) < p.num_docking_spots:
                    gstate.plan_miners[p.id].append(ship_id)
                    gstate.ships_targets[ship_id] = p.id
                else:
                    p = queue_planets(gmap, gstate, ship_id)
    # 4 player games
    else:
        #Determine if we start closer to left/right wall
        ship = gmap.get_me().all_ships()[0]
        if ship.x < gmap.width/2:
            gstate.leftright = 0
            logging.info('Determined left start')
        else:
            gstate.leftright = 1
            logging.info('Determined right start')

        #If enemy spawns within 1*max_speed units, go all in
        sid = gstate.all_ships[0]
        ship = gstate.gmap.get_me().get_ship(sid)
        enem = min(gstate.all_enems, key=ship.calculate_distance_between)
        if min_dist < 1*hlt.constants.MAX_SPEED:
            logging.info('Strategic: Executing All-In opening')
            gstate.add_squadron(closest_player.id, gstate.all_ships)
        else:
            logging.info('Strategic: Executing Early Scaling opening')
            p = 0
            ships = [gmap.get_me().get_ship(sid) for sid in gstate.all_ships]
            ships.sort(key=hlt.entity.Position(gmap.width/2, gmap.height/2).calculate_distance_between)
            gstate.all_ships = [ship.id for ship in ships]
            for ship_id in gstate.all_ships:
                if gstate.get_ship_role(ship_id) != 1:
                    gstate.set_ship_role(ship_id, 1)
                    gstate.ships_mine.append(ship_id)
                
                if not p:
                    p = queue_planets(gmap, gstate, ship_id)
                elif len(gstate.plan_miners[p.id]) < p.num_docking_spots:
                    gstate.plan_miners[p.id].append(ship_id)
                    gstate.ships_targets[ship_id] = p.id
                else:
                    p = queue_planets(gmap, gstate, ship_id)

def assign_ship_role(gstate, ship_id, count):
    '''
    Assign roles to new ships based on game state.
    '''
    ship = gstate.gmap.get_me().get_ship(ship_id)
    enem = min(gstate.all_enems, key=ship.calculate_distance_between)
    mother = min(gstate.gmap.all_planets(),
                 key=ship.calculate_distance_between)
    pprod = gstate.plan_prod.get(mother.id, 0)

    if gstate.plan_enems[mother.id]:
        return 2
    else:
        if gstate.turn <= 30:
            return 1
        else:
            return count%2 + 1


def queue_planets(gmap, gstate, ship_id):
    '''
    Assign miners to planets
    '''
    ship = gmap.get_me().get_ship(ship_id)

    planets = sorted(gmap.all_planets(),
                     key=lambda p: get_planet_priority(ship, gmap, gstate, p))

    for planet in planets:
        if len(gstate.plan_miners[planet.id]) < planet.num_docking_spots:
            gstate.plan_miners[planet.id].append(ship_id)
            gstate.ships_targets[ship_id] = planet.id
            return planet
        else:
            continue
    return None

def get_planet_priority(ship, gmap, gstate, target):
    """
    Calculates the order in which miners are allocated to planets.

    :return: priority
    :rtype: float
    """

    #4p games
    if gstate.n_players > 2:
        priority = math.sqrt((target.x - ship.x)**2 + (target.y - ship.y)**2)
        if gstate.leftright == 0:
            dist_from_side = target.calculate_distance_between(
                hlt.entity.Position(0, target.y))
        else:
            dist_from_side = target.calculate_distance_between(
                hlt.entity.Position(gmap.width, target.y))
        priority += math.sqrt(dist_from_side)
    #2p games
    else:
        priority = math.sqrt((target.x - ship.x)**2 + (target.y - ship.y)**2)/1.5
        center = hlt.entity.Position(gmap.width/2, gmap.height/2)
        p_radius = target.calculate_distance_between(center)

        priority += abs(p_radius - gstate.pstat_rdock_avg)
        if target.id < 4:
            priority = priority/2.5

    priority = priority/math.sqrt(target.num_docking_spots)

    return priority

def queue_attackers(ship, gmap, gstate):
    '''
    '''
    #find nearest of my planets, and nearest enemy to that planet
    # s = None
    # if gstate.plan_cap_cont:
    #     p = min(gstate.plan_cap_cont, key=ship.calculate_distance_between)
    #     s = gstate.plan_nearest_enem[p.id]
    # else:
    #     if gstate.all_enems:
    s = min(gstate.all_enems, key=ship.calculate_distance_between)

    #attack nearest enemy to nearest planet
    return s

def queue_guardians(gmap, gstate):
    '''
    '''
    for p in [p for p in gmap.all_planets() if p.owner == gmap.get_me()]:
        near_enems = gstate.plan_enems[p.id]
        n_enems = len(near_enems)
        n_guard = len(gstate.plan_guards.get(p.id, []))

        #Summon Guardians if n_enems > n_guardians
        if near_enems and (n_enems > n_guard):
            #Find nearby ships
            near_ships = [s for s in gmap.get_me().all_ships()
                          if (s.docking_status is hlt.entity.Ship.DockingStatus.UNDOCKED) \
                               and (s.role == 0 or s.role == 1 or s.role == 2) \
                               and (p.calculate_distance_between(s) \
                                    < p.radius + 3*hlt.constants.MAX_SPEED)]

            while (n_enems > n_guard) and near_ships:
                new_guard = min(near_ships, key=p.calculate_distance_between)
                gstate.ships_guar.append(new_guard.id)
                near_ships.remove(new_guard)
                gstate.set_ship_role(new_guard.id, 4)
                gstate.ships_targets[new_guard.id] = p
                gstate.plan_guards[p.id].append(new_guard.id)
                n_guard += 1
        #Release Guardians if n_enems < n_guardians
        elif n_enems < n_guard:
            while (n_enems < n_guard) and gstate.ships_guar:
                ship_id = gstate.ships_guar.pop()
                role = assign_ship_role(gstate, ship_id, gstate.ship_count)
                gstate.set_ship_role(ship_id, role)
                gstate.ship_count += 1
                if role == 1:
                    gstate.ships_mine.append(ship_id)
                elif role == 2:
                    gstate.ships_atck.append(ship_id)
                n_guard += -1