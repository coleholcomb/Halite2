import logging
import math
import time

import hlt

def mine_step(gmap, gstate):
    '''
    Assign commands to mining role ships
    '''
    commands = []

    while gstate.ships_mine:
        sid = gstate.ships_mine.pop()
        ship = gmap.get_me().get_ship(sid)

        # Skip docked ships
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            continue

        if time.time()-gstate.start >= 1.8:
            logging.warning('Out of time, ceasing commands')
            continue

        if gstate.ships_targets.get(sid, None) is None:
            p = hlt.strategy.queue_planets(gmap, gstate, sid)
        else:
            pid = gstate.ships_targets.get(sid, None)
            p = gmap.get_planet(pid)

        #Counter Cheese for init ships
        if ship.id in gstate.ships_init:
            navigate_command = init_mine_step(gmap, gstate, ship, p)
            if navigate_command:
                commands.append(navigate_command)
            continue

        # If no planets left to capture, convert to pure offense
        if p is None:
            gstate.set_ship_role(sid, 2)
            logging.info('Out of planets... Converting to Attack.')
            continue
        #if enemies docked on planet, attack them
        elif p.owner != gmap.get_me() and p.all_docked_ships():
            s = min(p.all_docked_ships(), key=ship.calculate_distance_between)

            navigate_command = ship.navigate(
                s,
                gmap,
                gstate,
                speed=int(hlt.constants.MAX_SPEED),
                max_corrections=60,
                angular_step=6,
                aux_list=gstate.undocked_enems)

            if navigate_command:
                commands.append(navigate_command)

        elif ship.can_dock(p):
            nearby_enems = [e for e in gstate.undocked_enems
                            if ship.calculate_distance_between(e) <= 5+ 2*hlt.constants.MAX_SPEED]
            nearby_allies = [s for s in gmap.get_me().all_ships()
                                if ship.docking_status == hlt.entity.Ship.DockingStatus.UNDOCKED
                                and ship.calculate_distance_between(s) <= 5+ 3*hlt.constants.MAX_SPEED]
            #don't dock if enemies are near
            if nearby_enems and (len(nearby_enems) > len(nearby_allies)):
                navigate_command = ship.navigate(
                    p,
                    gmap,
                    gstate,
                    speed=int(hlt.constants.MAX_SPEED),
                    max_corrections=180,
                    angular_step=2,
                    aux_list=gstate.undocked_enems)

                if navigate_command:
                    commands.append(navigate_command)
            # #aim to dock near already docked ships
            # elif p.all_docked_ships():
            #     docked_near = min(p.all_docked_ships(), key=ship.calculate_distance_between)
            #     dist = ship.calculate_distance_between(docked_near)
            #     if dist <= 3:
            #         commands.append(ship.dock(p))
            #     else:
            #         navigate_command = ship.navigate(
            #             docked_near,
            #             gmap,
            #             speed=int(hlt.constants.MAX_SPEED),
            #             max_corrections=180,
            #             angular_step=2,
            #             aux_list=gstate.undocked_enems)

            #         if navigate_command:
            #             commands.append(navigate_command)
            else:
                commands.append(ship.dock(p))
        else:
            navigate_command = ship.navigate(
                p,
                gmap,
                gstate,
                speed=int(hlt.constants.MAX_SPEED),
                max_corrections=60,
                angular_step=6,
                aux_list=gstate.undocked_enems)

            if navigate_command:
                commands.append(navigate_command)

    return commands

def init_mine_step(gmap, gstate, ship, planet):
    '''
    Constructs commands for initial miners
    '''
    nearby_all = [s for s in gmap.get_me().all_ships()
                  if (ship.calculate_distance_between(s) < 1.5*hlt.constants.MAX_SPEED)]
    nearby_undocked = [s for s in gmap.get_me().all_ships()
                       if (ship.calculate_distance_between(s) < 1.5*hlt.constants.MAX_SPEED)
                       and s.docking_status == hlt.entity.Ship.DockingStatus.UNDOCKED]
    attacking_enems = [e for e in gstate.undocked_enems
                       if ship.calculate_distance_between(e) <= 5 + 2*hlt.constants.MAX_SPEED]
    danger_enems = [e for e in gstate.undocked_enems
                    if ship.calculate_distance_between(e) <= (5 + 1.5*12/len(nearby_all))
                                                             *hlt.constants.MAX_SPEED]

    if ship.can_dock(planet):
        #if being attacked convert to flee class
        if attacking_enems and len(attacking_enems) >= len(nearby_all):
            logging.warning('Init Miners Fleeing!')
            gstate.set_ship_role(ship.id, 6)
            gstate.ships_flee.append(ship.id)
            return None
        #if within danger zone, wait for enemies to dock
        elif danger_enems and len(danger_enems) >= len(nearby_all):
            logging.warning('Init Miners Waiting...')
            return None
        #dock if no danger
        else:
            ship.docking_status = hlt.entity.Ship.DockingStatus.DOCKING
            return ship.dock(planet)
    #else head to planet
    else:
        navigate_command = ship.navigate(planet,
                                         gmap,
                                         gstate,
                                         speed=int(hlt.constants.MAX_SPEED),
                                         max_corrections=180,
                                         angular_step=2,
                                         aux_list=gstate.undocked_enems)
        return navigate_command
    
    return None

def atck_step(gmap, gstate):
    '''
    Constructs commands for attacking role ships
    '''
    commands = []
    while gstate.ships_atck:
        sid = gstate.ships_atck.pop()
        ship = gmap.get_me().get_ship(sid)

        s = hlt.strategy.queue_attackers(ship, gmap, gstate)
        if s is None:
            continue

        if ship.calculate_distance_between(s) > 12*hlt.constants.MAX_SPEED:
            gstate.set_ship_role(sid, 1)
            gstate.ships_mine.append(sid)
            continue

        if time.time()-gstate.start >= 1.8:
            logging.warning('Out of time, ceasing commands')
            continue

        navigate_command = ship.navigate(
            s,
            gmap,
            gstate,
            speed=int(hlt.constants.MAX_SPEED),
            ignore_ships=False,
            max_corrections=120,
            angular_step=3,
            aux_list=gstate.undocked_enems,
            aux_list2=gstate.ships_atck)

        if navigate_command:
            commands.append(navigate_command)

    return commands

def sqrn_step(gstate):
    '''
    Constructs commands for squadrons, issuing commands for several ships at once
    '''
    commands = []
    for squadron_id in gstate.squadrons.keys():
        squadron = gstate.squadrons[squadron_id]
        for cmd in squadron.navigate(gstate.undocked_enems):
            commands.append(cmd)
    return commands

def guar_step(gmap, gstate):
    '''
    '''
    commands = []
    while gstate.ships_guar:
        sid = gstate.ships_guar.pop()
        ship = gmap.get_me().get_ship(sid)

        p = gstate.ships_targets[sid]

        if gstate.plan_enems[p.id]:
            enem = min(gstate.plan_enems[p.id], key=ship.calculate_distance_between)
            s_protect = min(p.all_docked_ships(), key=enem.calculate_distance_between)
            target = enem.closest_point_to(s_protect)
            dist = ship.calculate_distance_between(target)

            if dist > 1:
                navigate_command = ship.navigate(
                    target,
                    gmap,
                    gstate,
                    speed=min(dist, hlt.constants.MAX_SPEED),
                    ignore_ships=False,
                    max_corrections=180,
                    angular_step=2)

                if navigate_command:
                    commands.append(navigate_command)

    return commands

def corn_step(gmap, gstate):
    '''
    Assign commands to corner role ships
    '''
    commands = []

    while gstate.ships_corn:
        sid = gstate.ships_corn.pop()
        ship = gmap.get_me().get_ship(sid)

        # Skip docked ships
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            continue

        if time.time()-gstate.start >= 1.8:
            logging.warning('Out of time, ceasing commands')
            continue

        if gstate.ships_targets.get(sid, None) is None:
            targets = [hlt.entity.Position(1., 1.), 
                       hlt.entity.Position(1., gmap.height-1.),
                       hlt.entity.Position(gmap.width-1., 1.), 
                       hlt.entity.Position(gmap.width-1., gmap.height-1.)]

            target = min(targets, key=ship.calculate_distance_between)
            gstate.ships_targets[sid] = target
        else:
            target = gstate.ships_targets.get(sid, None)

        navigate_command = ship.navigate(
            target,
            gmap,
            gstate,
            speed=int(hlt.constants.MAX_SPEED),
            max_corrections=60,
            angular_step=6,
            aux_list=gstate.undocked_enems)

        if navigate_command:
            commands.append(navigate_command)

    return commands

def flee_step(gmap, gstate):
    '''
    Assign commands to ships fleeing enemy attackers
    '''
    commands = []
    while gstate.ships_flee:
        sid = gstate.ships_flee.pop()
        ship = gmap.get_me().get_ship(sid)
        logging.warning('Fleeeeee')

        enems = [e for e in gstate.all_enems
                 if ship.calculate_distance_between(e) <= 25*hlt.constants.MAX_SPEED]
        if not enems:
            logging.warning('Danger has been fled, return to mining')
            gstate.set_ship_role(ship.id, 1)
            gstate.ships_mine.append(ship.id)
            continue

        near_enems = [e for e in gstate.all_enems
                      if ship.calculate_distance_between(e) <= 5*hlt.constants.MAX_SPEED]

        #fly away from all nearby ships
        #first move away from allies
        if near_enems:
            target = hlt.entity.Position(ship.x, ship.y)
        else:
            nearest_enem = min(enems, key=ship.calculate_distance_between)
            # planets = [p for p in gmap.all_planets() 
            #            if p.calculate_distance_between(nearest_enem) > 15*hlt.constants.MAX_SPEED]
            p = min(gmap.all_planets(), key=ship.calculate_distance_between)
            target = hlt.entity.Position(p.x, p.y)

        near_allies = [s for s in gmap.get_me().all_ships() if ship.id != s.id
                       and ship.calculate_distance_between(s) < 2*hlt.constants.MAX_SPEED]
        if near_allies:
            nearest_ally = min([s for s in gmap.get_me().all_ships() if ship.id != s.id],
                               key=ship.calculate_distance_between)
            angle = nearest_ally.calculate_angle_between(ship)
            magn = hlt.constants.MAX_SPEED
            target = target + hlt.entity.Position(ship.x + math.cos(math.radians(angle))*magn,
                                                  ship.y + math.sin(math.radians(angle))*magn)
        #then move away from enems
        for e in near_enems:
            e_angl = e.calculate_angle_between(ship)
            e_magn = hlt.constants.MAX_SPEED
            target = target + hlt.entity.Position(math.cos(math.radians(e_angl))*e_magn,
                                                  math.sin(math.radians(e_angl))*e_magn)

        navigate_command = ship.navigate(target,
                                         gmap,
                                         gstate,
                                         speed=int(hlt.constants.MAX_SPEED),
                                         max_corrections=60,
                                         angular_step=6,
                                         aux_list=gstate.undocked_enems)
        if navigate_command:
            commands.append(navigate_command)

    return commands
