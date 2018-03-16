import logging
import math
import time
from collections import defaultdict

import hlt

class State:
    '''
    Stores state info

    TODO:
     manage ship roles
     manage planets
    '''
    def __init__(self):
        self.start = 0

        self.gmap = None
        self.turn = -1
        self.n_players = 0
        self.player_docks = {}

        self.leftright = None #0 = left start, 1 = right start

        self.pstat_Ndocks = 0
        self.pstat_rdock_avg = 0
        self.pstat_xdock_avg = 0
        self.pstat_ydock_avg = 0
        self.pstat_rdock_rms = 0

        self.all_planets = []
        self.plan_empty = []
        self.plan_cap = []
        self.plan_cap_cont = []
        self.plan_uncap = []
        self.plan_enem = []
        self.plan_miners = defaultdict(list) #miners assigned to planet
        self.plan_guards = defaultdict(list) #guardians assigned to planet
        self.plan_enems = defaultdict(list) #enemys attacking my planets
        self.plan_nearest_enem = {} #nearest enemy to each planet
        self.plan_prod = {} #current ship output rates
        self.max_production = 0

        self.all_ships = [] #Specifically ships belonging to me
        self.ships_roles = {}
        self.ships_targets = {}
        self.ships_mine = []
        self.ships_atck = []
        self.ships_guar = []
        self.ships_corn = []
        self.ships_flee = []
        self.ships_init = []
        self.ships_hunt = [] #not yet implemented
        self.ships_gath = [] #not yet implemented

        self.squadrons = {}
        self.squadron_cnt = 0

        self.nships = 0 #for tracking current number of ships
        self.ship_count = 3 #for assigning ship roles

        self.all_enems = []
        self.all_enems_ids = []
        self.docked_enems = []
        self.undocked_enems = []
        self.enems_positions = {}
        self.enem_nearest_atck = {}

    def update(self, gmap):
        '''
        Update all state information
        '''
        self.start = time.time()
        self.gmap = gmap

        self.turn += 1
        self.n_players = len(self.gmap.all_players())

        self.update_planets_1()
        logging.warning('Planets')
        self.update_enems() #Strictly enemy ships
        logging.warning('Enems')
        self.update_ships() #Strictly my ships
        logging.warning('Ships')
        self.update_planets_2()
        logging.warning('Planets 2')

        #print log info
        logging.info('Turn: '+str(self.turn)+'. State updated in '
                     +str(time.time()-self.start)+' seconds')
        logging.info('n_miners '+str(len(self.ships_mine)))
        logging.info('n_attackers '+str(len(self.ships_atck)))
        logging.info('n_guardians '+str(len(self.ships_guar)))
        logging.info('n_corners '+str(len(self.ships_corn)))
        for player_id in self.player_docks.keys():
            logging.info('player '+str(player_id)+' production '
                         + str(self.player_docks[player_id]))

    def assess_planets(self):
        '''
        Calculate properties of planet distribution
        '''
        #total docking spots
        self.pstat_Ndocks = 0
        for p in self.gmap.all_planets():
            self.pstat_Ndocks += p.num_docking_spots

        #average location of docking spots
        center = hlt.entity.Position(self.gmap.width/2, self.gmap.height/2)
        self.pstat_rdock_avg = 0
        for p in self.gmap.all_planets():
            self.pstat_rdock_avg += p.calculate_distance_between(center)*p.num_docking_spots
            self.pstat_xdock_avg += abs(p.x - self.gmap.width/2)*p.num_docking_spots
            self.pstat_ydock_avg += abs(p.y - self.gmap.width/2)*p.num_docking_spots
            self.pstat_rdock_rms += (p.calculate_distance_between(center))**2 *p.num_docking_spots
        self.pstat_rdock_avg = self.pstat_rdock_avg/self.pstat_Ndocks
        self.pstat_xdock_avg = self.pstat_xdock_avg/self.pstat_Ndocks
        self.pstat_ydock_avg = self.pstat_ydock_avg/self.pstat_Ndocks
        self.pstat_rdock_rms = math.sqrt(self.pstat_rdock_rms/self.pstat_Ndocks)

        logging.info('Planetary Stats: Total docking spots = '+str(self.pstat_Ndocks))
        logging.info('Planetary Stats: Average docking spot radius = '+str(self.pstat_rdock_avg))
        logging.info('Planetary Stats: Average docking spot x = '+str(self.pstat_xdock_avg))
        logging.info('Planetary Stats: Average docking spot y = '+str(self.pstat_ydock_avg))
        logging.info('Planetary Stats: RMS docking spot radius = '+str(self.pstat_rdock_rms))

    def update_planets_1(self):
        '''
        Update state information regarding planets that doesn't rely on
        ship state
        '''
        #clear player docking numbers
        for player in self.gmap.all_players():
            self.player_docks[player.id] = 0

        self.max_production = 0
        for p in self.gmap.all_planets():
            self.max_production += p.num_docking_spots/12.
            if p.is_owned():
                self.plan_prod[p.id] = p.current_production
                self.player_docks[p.owner.id] += len(p.all_docked_ships())/12.

        planets = [p.id for p in self.gmap.all_planets()]
        planets_rem = [pid for pid in self.all_planets if pid not in planets]
        self.all_planets = planets

        for pid in planets:
            self.plan_prod[pid] = len(self.gmap.get_planet(pid).all_docked_ships())/12.

        self.plan_empty = [planet for planet in self.gmap.all_planets()
                           if planet.owner is None]
        self.plan_enem = [planet for planet in self.gmap.all_planets()
                           if (planet.owner != self.gmap.get_me()
                               and planet.owner is not None)]
        self.plan_uncap = [planet for planet in self.gmap.all_planets()
                           if planet.owner != self.gmap.get_me()]
        self.plan_cap = [planet for planet in self.gmap.all_planets()
                         if planet.owner == self.gmap.get_me()
                         and not planet.is_full()]
        self.plan_cap_cont = [planet for planet in self.gmap.all_planets()
                              if planet.owner == self.gmap.get_me()]

    def update_planets_2(self):
        '''
        Update state information regarding planets that relies on
        state of my and enemies ships

        Trigger hiding in corner for 4p games
        Summon/release guardians
        '''
        #Initiate retreat if conditions are met
        if self.n_players > 2:
            my_id = self.gmap.get_me().id
            nearest_id = (my_id + 2)%4
            if (self.player_docks[nearest_id] > 2*self.player_docks[my_id]) \
                and (self.player_docks[nearest_id] > 1):
                logging.info('Initiate retreat')
                for sid in self.all_ships:
                    if self.ships_roles[sid] != 5:
                        self.set_ship_role(sid, 5)
                        self.ships_corn.append(sid)
            else:
                for player_id in [(my_id + 1)%4, (my_id + 3)%4]:
                    if self.player_docks[player_id] > .6*self.max_production:
                        logging.info('Initiate retreat')
                        for sid in self.all_ships:
                            if self.ships_roles[sid] != 5:
                                self.set_ship_role(sid, 5)
                                self.ships_corn.append(sid)

        #Clear planets' nearby enemy dicts
        planets = self.gmap.all_planets()
        for p in planets:
            if self.all_enems:
                self.plan_nearest_enem[p.id] = min(self.all_enems,
                                                   key=p.calculate_distance_between)
            self.plan_enems.get(p.id, []).clear()

        enems = self.undocked_enems[:]
        while enems and planets:
            e = enems.pop()
            near_p = min(planets, key=e.calculate_distance_between)
            if near_p.owner == self.gmap.get_me():
                s = near_p.all_docked_ships()[0]
            else:
                s = near_p
            if s.calculate_distance_between(e) < near_p.radius + 2*hlt.constants.MAX_SPEED:
                self.plan_enems[near_p.id].append(e)

        hlt.strategy.queue_guardians(self.gmap, self)

    def update_ships(self):
        '''
        Update state information regarding my ships
        '''
        ships = [s.id for s in self.gmap.get_me().all_ships()]
        ships_add = [sid for sid in ships if sid not in self.all_ships]
        ships_rem = [sid for sid in self.all_ships if sid not in ships]
        self.all_ships = ships
        self.nships = len(self.all_ships)
        self.add_ships(ships_add)
        self.rem_ships(ships_rem)

        self.ships_mine = [sid for sid in self.ships_roles.keys()
                           if self.ships_roles[sid] == 1]
        self.ships_atck = [sid for sid in self.ships_roles.keys()
                           if self.ships_roles[sid] == 2]
        self.ships_guar = [sid for sid in self.ships_roles.keys()
                           if self.ships_roles[sid] == 4]
        self.ships_corn = [sid for sid in self.ships_roles.keys()
                           if self.ships_roles[sid] == 5]
        self.ships_flee = [sid for sid in self.ships_roles.keys()
                           if self.ships_roles[sid] == 6]

        self.ships_hunt = [] #not yet implemented
        self.ships_gath = [] #not yet implemented

        for ship in self.gmap.get_me().all_ships():
            ship.role = self.ships_roles.get(ship.id, 0)

    def add_ships(self, ships):
        '''
        Process newly created ships.

        Add new ships to ships_roles dictionary.
        '''
        #set ship roles
        for ship_id in ships:
            role = hlt.strategy.assign_ship_role(self, ship_id, self.ship_count)
            #role = self.ship_count%2 + 1
            self.set_ship_role(ship_id, role)
            self.ship_count += 1

    def rem_ships(self, ships):
        '''
        Process newly destroyed ships.
        '''
        for ship_id in ships:
            self.clean_ship(ship_id)

    def set_ship_role(self, ship_id, role):
        '''
        Set the role for a ship:
        0: Unassigned
        1: Miner
        2: Attacker
        3: Attacker in Squadron
        4: Guardian
        5: Corner
        6: Flee

        First clean previous role,
        Then set role
        '''
        self.clean_ship(ship_id)
        self.ships_roles[ship_id] = role
        self.gmap.get_me().get_ship(ship_id).role = role

    def get_ship_role(self, ship_id):
        '''
        Return the integer value of the ship's role
        0: Unassigned
        1: Miner
        2: Attacker
        3: Sqaudron
        4: Guardian
        5: Corner
        6: Flee
        '''
        return self.ships_roles.get(ship_id, 0)

    def update_enems(self):
        '''
        Update state information regarding enemy ships.

        Including enemy movement predictions
        '''
        enems = [e for e in self.gmap.all_enem_ships()]
        enems_ids = [e.id for e in self.gmap.all_enem_ships()]
        enems_old = [e.id for e in enems if e.id in self.all_enems_ids]
        enems_add = [e for e in enems if e.id not in self.all_enems_ids]
        enems_rem = [e for e in self.all_enems if e.id not in enems_ids]
        self.all_enems = enems
        self.all_enems_ids = enems_ids
        self.docked_enems = [e for e in self.all_enems if e.docking_status
                             is not hlt.entity.Ship.DockingStatus.UNDOCKED]
        self.undocked_enems = [e for e in self.all_enems if e.docking_status
                               is hlt.entity.Ship.DockingStatus.UNDOCKED]
        self.rem_enems(enems_rem)

        for e in self.gmap._all_ships():
            if e.owner.id == self.gmap.get_me().id:
                continue
            
            _ = self.enem_nearest_atck.pop(e.id, 0)
            self.enem_nearest_atck[e.id] = min(self.gmap.get_me().all_ships(),
                                               key=e.calculate_distance_between).id

            if e.id in enems_old:
                x0, y0 = self.enems_positions[e.id].x, self.enems_positions[e.id].y
                dx, dy = e.x - x0, e.y - y0
                magn = int(math.sqrt(dx**2 + dy**2))
                if magn == 0:
                    e.thrust_cmd = None
                else:
                    p0 = hlt.entity.Position(x0, y0)
                    angl = p0.calculate_angle_between(e)
                    e.thrust_cmd = hlt.entity.Thrust(e, magn, angl)
            else:
                e.thrust_cmd = None

            self.enems_positions[e.id] = e

        self.add_enems(enems_add)

    def add_enems(self, add):
        '''
        Store state data on newly created enemy ships
        '''
        for e in add:
            self.enems_positions[e.id] = e

    def rem_enems(self, rem):
        '''
        remove destoryed enemy ships from state storage
        '''
        for e in rem:
            _ = self.enem_nearest_atck.pop(e.id, 0)
            _ = self.enems_positions.pop(e.id, 0)


    def add_squadron(self, target_player_id, ship_ids):
        '''
        '''
        squad_id = self.squadron_cnt
        self.squadrons[id] = hlt.entity.Squadron(self, target_player_id, squad_id, ship_ids)
        self.squadron_cnt += 1

    def disband_squadron(self, squadron):
        '''
        '''
        #reassign ships to miners
        logging.info('Disband squadron '+str(squadron.ship_ids))
        for sid in squadron.ship_ids[:]:
            self.set_ship_role(sid, 1)
            self.ships_mine.append(sid)

        #remove squadron from squadrons dict
        _ = self.squadrons.pop(squadron.id, None)

    def clean_ship(self, ship_id):
        '''
        When changing roles or deleting ships, remove ship from
        all State structures involved in previous role
        '''
        #remove ships from roles dictionary
        role = self.ships_roles.pop(ship_id, None)
        #remove ships from ships targets dictionary
        target_id = self.ships_targets.pop(ship_id, None)

        #Miners
        if role == 1:
            #Try to remove from ships_mine list
            try:
                self.ships_mine.remove(ship_id)
            except ValueError:
                pass
            #try to remove from planets miners dict
            if target_id is not None:
                try:
                    self.plan_miners[target_id].remove(ship_id)
                except ValueError:
                    pass
        #Attackers
        elif role == 2:
            #Try to remove from ships_atck list
            try:
                self.ships_atck.remove(ship_id)
            except ValueError:
                pass
        #Squadrons
        elif role == 3:
            for squad_id in self.squadrons.keys():
                squadron = self.squadrons[squad_id]
                try:
                    squadron.ship_ids.remove(ship_id)
                except ValueError:
                    pass
        #Guardians
        elif role == 4:
            #Try to remove from ships_guar list
            try:
                self.ships_guar.remove(ship_id)
            except ValueError:
                pass
            #Try to remove from planets guardians dict
            if target_id is not None:
                try:
                    self.plan_guards[target_id].remove(ship_id)
                except ValueError:
                    pass
        elif role == 6:
            #Try to remove from ships_flee list
            try:
                self.ships_flee.remove(ship_id)
            except ValueError:
                pass