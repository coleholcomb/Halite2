import logging
import math

from . import collision, constants
import abc
from enum import Enum


class Entity:
    """
    Then entity abstract base-class represents all game entities possible. As a base all entities possess
    a position, radius, health, an owner and an id. Note that ease of interoperability, Position inherits from
    Entity.

    :ivar id: The entity ID
    :ivar x: The entity x-coordinate.
    :ivar y: The entity y-coordinate.
    :ivar radius: The radius of the entity (may be 0)
    :ivar health: The planet's health.
    :ivar owner: The player ID of the owner, if any. If None, Entity is not owned.
    """
    __metaclass__ = abc.ABCMeta

    def _init__(self, x, y, radius, health, player, entity_id):
        self.x = x
        self.y = y
        self.radius = radius
        self.health = health
        self.owner = player
        self.id = entity_id

    def calculate_distance_between(self, target):
        """
        Calculates the distance between this object and the target.

        :param Entity target: The target to get distance to.
        :return: distance
        :rtype: float
        """
        return math.sqrt((target.x - self.x) ** 2 + (target.y - self.y) ** 2)

    def calculate_angle_between(self, target):
        """
        Calculates the angle between this object and the target in degrees.

        :param Entity target: The target to get the angle between.
        :return: Angle between entities in degrees
        :rtype: float
        """
        return math.degrees(math.atan2(target.y - self.y, target.x - self.x)) % 360

    def closest_point_to(self, target, min_distance=1):
        """
        Find the closest point to the given ship near the given target, outside its given radius,
        with an added fudge of min_distance.

        :param Entity target: The target to compare against
        :param int min_distance: Minimum distance specified from the object's outer radius
        :return: The closest point's coordinates
        :rtype: Position
        """
        angle = target.calculate_angle_between(self)
        radius = target.radius + min_distance
        x = target.x + radius * math.cos(math.radians(angle))
        y = target.y + radius * math.sin(math.radians(angle))

        return Position(x, y)

    @abc.abstractmethod
    def _link(self, players, planets):
        pass

    def __str__(self):
        return "Entity {} (id: {}) at position: (x = {}, y = {}), with radius = {}"\
            .format(self.__class__.__name__, self.id, self.x, self.y, self.radius)

    def __repr__(self):
        return self.__str__()


class Planet(Entity):
    """
    A planet on the game map.

    :ivar id: The planet ID.
    :ivar x: The planet x-coordinate.
    :ivar y: The planet y-coordinate.
    :ivar radius: The planet radius.
    :ivar num_docking_spots: The max number of ships that can be docked.
    :ivar current_production: How much production the planet has generated at the moment. Once it reaches the threshold, a ship will spawn and this will be reset.
    :ivar remaining_resources: The remaining production capacity of the planet.
    :ivar health: The planet's health.
    :ivar owner: The player ID of the owner, if any. If None, Entity is not owned.

    """

    def __init__(self, planet_id, x, y, hp, radius, docking_spots, current,
                 remaining, owned, owner, docked_ships):
        self.id = planet_id
        self.x = x
        self.y = y
        self.radius = radius
        self.num_docking_spots = docking_spots
        self.current_production = current
        self.remaining_resources = remaining
        self.health = hp
        self.owner = owner if bool(int(owned)) else None
        self._docked_ship_ids = docked_ships
        self._docked_ships = {}

    def get_docked_ship(self, ship_id):
        """
        Return the docked ship designated by its id.

        :param int ship_id: The id of the ship to be returned.
        :return: The Ship object representing that id or None if not docked.
        :rtype: Ship
        """
        return self._docked_ships.get(ship_id)

    def all_docked_ships(self):
        """
        The list of all ships docked into the planet

        :return: The list of all ships docked
        :rtype: list[Ship]
        """
        return list(self._docked_ships.values())

    def is_owned(self):
        """
        Determines if the planet has an owner.
        :return: True if owned, False otherwise
        :rtype: bool
        """
        return self.owner is not None

    def is_full(self):
        """
        Determines if the planet has been fully occupied (all possible ships are docked)

        :return: True if full, False otherwise.
        :rtype: bool
        """
        return len(self._docked_ship_ids) >= self.num_docking_spots

    def _link(self, players, planets):
        """
        This function serves to take the id values set in the parse function and use it to populate the planet
        owner and docked_ships params with the actual objects representing each, rather than IDs

        :param dict[int, gane_map.Player] players: A dictionary of player objects keyed by id
        :return: nothing
        """
        if self.owner is not None:
            self.owner = players.get(self.owner)
            for ship in self._docked_ship_ids:
                self._docked_ships[ship] = self.owner.get_ship(ship)

    @staticmethod
    def _parse_single(tokens):
        """
        Parse a single planet given tokenized input from the game environment.

        :return: The planet ID, planet object, and unused tokens.
        :rtype: (int, Planet, list[str])
        """
        (plid, x, y, hp, r, docking, current, remaining,
         owned, owner, num_docked_ships, *remainder) = tokens

        plid = int(plid)
        docked_ships = []

        for _ in range(int(num_docked_ships)):
            ship_id, *remainder = remainder
            docked_ships.append(int(ship_id))

        planet = Planet(int(plid),
                        float(x), float(y),
                        int(hp), float(r), int(docking),
                        int(current), int(remaining),
                        bool(int(owned)), int(owner),
                        docked_ships)

        return plid, planet, remainder

    @staticmethod
    def _parse(tokens):
        """
        Parse planet data given a tokenized input.

        :param list[str] tokens: The tokenized input
        :return: the populated planet dict and the unused tokens.
        :rtype: (dict, list[str])
        """
        num_planets, *remainder = tokens
        num_planets = int(num_planets)
        planets = {}

        for _ in range(num_planets):
            plid, planet, remainder = Planet._parse_single(remainder)
            planets[plid] = planet

        return planets, remainder


class Ship(Entity):
    """
    A ship in the game.

    :ivar id: The ship ID.
    :ivar x: The ship x-coordinate.
    :ivar y: The ship y-coordinate.
    :ivar radius: The ship radius.
    :ivar health: The ship's remaining health.
    :ivar DockingStatus docking_status: The docking status (UNDOCKED, DOCKED, DOCKING, UNDOCKING)
    :ivar planet: The ID of the planet the ship is docked to, if applicable.
    :ivar owner: The player ID of the owner, if any. If None, Entity is not owned.
    """

    class DockingStatus(Enum):
        UNDOCKED = 0
        DOCKING = 1
        DOCKED = 2
        UNDOCKING = 3

    def __init__(self, player_id, ship_id, x, y, hp, vel_x, vel_y,
                 docking_status, planet, progress, cooldown):
        self.id = ship_id
        self.x = x
        self.y = y
        self.owner = player_id
        self.radius = constants.SHIP_RADIUS
        self.health = hp
        self.docking_status = docking_status
        self.planet = planet if (docking_status is not Ship.DockingStatus.UNDOCKED) else None
        self._docking_progress = progress
        self._weapon_cooldown = cooldown

        self.thrust_cmd = None
        self.role = 0

    def thrust(self, magnitude, angle):
        """
        Generate a command to accelerate this ship.

        :param int magnitude: The speed through which to move the ship
        :param int angle: The angle to move the ship in
        :return: The command string to be passed to the Halite engine.
        :rtype: str
        """

        # we want to round angle to nearest integer, but we want to round
        # magnitude down to prevent overshooting and unintended collisions
        self.thrust_cmd = Thrust(self, int(magnitude), round(angle))
        return "t {} {} {}".format(self.id, int(magnitude), round(angle))

    def dock(self, planet):
        """
        Generate a command to dock to a planet.

        :param Planet planet: The planet object to dock to
        :return: The command string to be passed to the Halite engine.
        :rtype: str
        """
        return "d {} {}".format(self.id, planet.id)

    def undock(self):
        """
        Generate a command to undock from the current planet.

        :return: The command trying to be passed to the Halite engine.
        :rtype: str
        """
        return "u {}".format(self.id)

    def navigate(self, target, game_map, gstate, speed, avoid_obstacles=True,
                 max_corrections=90, angular_step=1, ignore_ships=False,
                 ignore_planets=False, aux_list=[], aux_list2=[],
                 ignore_list=[]):
        """
        Move a ship to a specific target position (Entity). It is recommended to place the position
        itself here, else navigate will crash into the target. If avoid_obstacles is set to True (default)
        will avoid obstacles on the way, with up to max_corrections corrections. Note that each correction accounts
        for angular_step degrees difference, meaning that the algorithm will naively try max_correction degrees before giving
        up (and returning None). The navigation will only consist of up to one command; call this method again
        in the next turn to continue navigating to the position.

        :param Entity target: The entity to which you will navigate
        :param game_map.Map game_map: The map of the game, from which obstacles will be extracted
        :param int speed: The (max) speed to navigate. If the obstacle is nearer, will adjust accordingly.
        :param bool avoid_obstacles: Whether to avoid the obstacles in the way (simple pathfinding).
        :param int max_corrections: The maximum number of degrees to deviate per turn while trying to pathfind. If exceeded returns None.
        :param int angular_step: The degree difference to deviate if the original destination has obstacles
        :param bool ignore_ships: Whether to ignore ships in calculations (this will make your movement faster, but more precarious)
        :param bool ignore_planets: Whether to ignore planets in calculations (useful if you want to crash onto planets)
        :return string: The command trying to be passed to the Halite engine or None if movement is not possible within max_corrections degrees.
        :rtype: str
        """

        if self.role == 1:
            return self.navigate_miner(target, game_map, gstate, speed, 
                                max_corrections=max_corrections,
                                angular_step=angular_step, aux_list=aux_list)
        elif self.role == 2:
            return self.navigate_attacker(target, game_map, gstate, speed, 
                                max_corrections=max_corrections,
                                angular_step=angular_step, aux_list=aux_list,
                                aux_list2=aux_list2)
        elif self.role == 3:
            return self.navigate_squadron(target, game_map, gstate, speed, 
                                max_corrections=max_corrections,
                                angular_step=angular_step, aux_list=aux_list, 
                                aux_list2=aux_list2, ignore_list=ignore_list)
        elif self.role == 4:
            return self.navigate_guardian(target, game_map, gstate, speed, 
                                max_corrections=max_corrections,
                                angular_step=angular_step, aux_list=aux_list)
        elif self.role == 5:
            return self.navigate_corner(target, game_map, gstate, speed, 
                                max_corrections=max_corrections,
                                angular_step=angular_step, aux_list=aux_list)
        elif self.role == 6:
            return self.navigate_flee(target, game_map, gstate, speed)
        else:
            return self.thrust(0, 0)

    def navigate_miner(self, target, game_map, gstate, speed, avoid_obstacles=True,
                       max_corrections=90, angular_step=1, ignore_ships=False,
                       ignore_planets=False, aux_list=[], aux_list2=[]):
        '''
        aux_list = undocked enemies
        '''
        closest_point_target = self.closest_point_to(target)
        dist_to_closest = self.calculate_distance_between(closest_point_target)

        angle = self.calculate_angle_between(closest_point_target)
        distance = speed if (dist_to_closest >= speed) else int(dist_to_closest)
        new_target_dx = math.cos(math.radians(angle)) * distance
        new_target_dy = math.sin(math.radians(angle)) * distance
        new_target = Position(self.x + new_target_dx, self.y + new_target_dy)

        #Find nearest enem ships
        nearby_enems = [e for e in gstate.undocked_enems
                        if self.calculate_distance_between(e) <= 5 + constants.MAX_SPEED]
        nearby_allies = [s for s in game_map.get_me().all_ships()
                         if (s.role == 1 or s.role == 2)
                         and self.calculate_distance_between(s) <= 5 + constants.MAX_SPEED]
        #if there are nearby enemies, and outnumbered, evade them
        if nearby_enems and (len(nearby_enems) >= len(nearby_allies)):
            #add enemy thrust vectors to target vector
            #assume enemy thrusts toward my ship
            for e in nearby_enems:
                e_angl = e.calculate_angle_between(self)
                e_magn = constants.MAX_SPEED
                new_target = new_target + Position(math.cos(math.radians(e_angl))*e_magn,
                                                   math.sin(math.radians(e_angl))*e_magn)
            closest_point_target = self.closest_point_to(new_target)
            dist_to_closest = self.calculate_distance_between(closest_point_target)

            angle = self.calculate_angle_between(closest_point_target)
            vel = speed if (dist_to_closest >= speed) else int(dist_to_closest)
            new_target_dx = math.cos(math.radians(angle)) * vel
            new_target_dy = math.sin(math.radians(angle)) * vel
            new_target = Position(self.x + new_target_dx, self.y + new_target_dy)
            t = self.navigate_iter(game_map, new_target, vel, 3, 20)
            if t is None:
                t = self.navigate_iter(game_map, new_target, vel, 6, 20)
            if t is None:
                t = self.navigate_iter(game_map, new_target, vel, 18, 20)
            if t is None:
                return self.thrust(0, 0)
            else:
                return t
        #else attack docked enemies
        else:
            vel = distance
            t = self.navigate_iter(game_map, new_target, vel, 3, 20, aux_list=nearby_enems)
            if t is None:
                vel = max(vel-2, 1)
                t = self.navigate_iter(game_map, new_target, vel, 6, 20, aux_list=nearby_enems)
            if t is None:
                vel = max(vel-2, 1)
                t = self.navigate_iter(game_map, new_target, vel, 18, 20, aux_list=nearby_enems)
            if t is None:
                return self.thrust(0, 0)
            else:
                return t

    def navigate_iter(self, gmap, target, vel, angular_step, iter, aux_list=[], ignore_list=[]):
        '''
        '''
        angle_coef = 0
        max_corrections = iter
        while max_corrections >= 0:
            angle = self.calculate_angle_between(target)

            test_thrust = Thrust(self, vel, angle)
            thrust_conflict = self.thrust_overlap(gmap, test_thrust)

            ignore = ()
            obstacles = gmap.obstacles_between(self, target, ignore)
            if ignore_list:
                obstacles = [o for o in obstacles if o not in ignore_list]

            if aux_list and (self.role == 1  or self.role == 2 or self.role == 3):
                aux_conflict = self.evade_enems(gmap, test_thrust, aux_list)
            else:
                aux_conflict = False

            if any([obstacles, thrust_conflict, aux_conflict]):
                new_target_dx = math.cos(math.radians(angle
                                                      + angle_coef*angular_step))*vel
                new_target_dy = math.sin(math.radians(angle
                                                      + angle_coef*angular_step))*vel
                target = Position(self.x + new_target_dx, self.y + new_target_dy)

                max_corrections += -1
                angle_coef = (abs(angle_coef) + 1) * (-1)**(max_corrections)
            else:
                return self.thrust(vel, angle)

        return None

    def navigate_attacker(self, target, game_map, gstate, speed, avoid_obstacles=True,
                          max_corrections=90, angular_step=1, ignore_ships=False,
                          ignore_planets=False, aux_list=[], aux_list2=[]):
        '''

        '''
        #Find nearby enem ships
        nearby_enems = [e for e in gstate.undocked_enems
                        if self.calculate_distance_between(e) <= 5 + 2*constants.MAX_SPEED]

        #if not closest ship to target, go to closest ship
        if self.id != gstate.enem_nearest_atck[target.id]:
            target = game_map.get_me().get_ship(gstate.enem_nearest_atck[target.id])
            if target.thrust_cmd:
                target = Position(target.thrust_cmd.x1, target.thrust_cmd.y1)
                target.radius = constants.SHIP_RADIUS
        #else wait for reinforcements before attacking
        else:
            if nearby_enems:
                #Find nearby ally ships
                nearby_allies = [s for s in game_map.get_me().all_ships()
                                 if s.role == 2
                                 and self.calculate_distance_between(s) <= 5]
                if len(nearby_enems) >= .8*len(nearby_allies):
                    #find nearest ally not in nearby_allies
                    far_allies = [s for s in game_map.get_me().all_ships()
                                  if s.role == 2
                                  and self.calculate_distance_between(s) > 5]
                    #If no allied undocked ships, head for the docks
                    if not far_allies:
                        far_allies = [s for s in game_map.get_me().all_ships()
                                      if s.role == 1]
                    #Else move to nearest undocked ally
                    else:
                        target = min(far_allies, key=self.calculate_distance_between)
                        #Aim for their future position
                        if target.thrust_cmd:
                            target = Position(target.thrust_cmd.x1, target.thrust_cmd.y1)
                            target.radius = constants.SHIP_RADIUS

        closest_point_target = self.closest_point_to(target)
        dist_to_closest = self.calculate_distance_between(closest_point_target)
        #backtrack from moving enemy ships
        # if isinstance(target, Ship) and (target.docking_status is Ship.DockingStatus.UNDOCKED) \
        #    and (dist_to_closest < 2*constants.MAX_SPEED) \
        #    and target.owner is not game_map.get_me():
        #     #assume enemy thrusts towards you with vel = distance
        #     angle = target.calculate_angle_between(self)
        #     vel = min(2*constants.MAX_SPEED - dist_to_closest + 2, constants.MAX_SPEED)
        #     new_target = Position(self.x + math.cos(math.radians(angle))*vel,
        #                           self.y + math.sin(math.radians(angle))*vel)
        #     vel=abs(vel)
        #     logging.warning('target is moving ship')
        # else:
        angle = self.calculate_angle_between(closest_point_target)
        vel = speed if (dist_to_closest >= speed) else int(dist_to_closest)
        new_target_dx = math.cos(math.radians(angle))*vel
        new_target_dy = math.sin(math.radians(angle))*vel
        new_target = Position(self.x + new_target_dx, self.y + new_target_dy)

        t = self.navigate_iter(game_map, new_target, vel, 3, 20, aux_list=nearby_enems)
        if t is None:
            vel = max(vel-2, 1)
            t = self.navigate_iter(game_map, new_target, vel, 6, 20, aux_list=nearby_enems)
        if t is None:
            vel = max(vel-2, 1)
            t = self.navigate_iter(game_map, new_target, vel, 18, 20, aux_list=nearby_enems)
        if t is None:
            return self.thrust(0, 0)
        else:
            return t

    def navigate_squadron(self, target, game_map, gstate, speed, avoid_obstacles=True,
                          max_corrections=90, angular_step=1, ignore_ships=False, 
                          ignore_planets=False, aux_list=[], aux_list2=[], ignore_list=[]):
        '''
        Give navigation commands to squadron ships.

        Hunt down target player while avoiding collisions with moving enemy ships.
        '''
        
        closest_point_target = self.closest_point_to(target)
        dist_to_closest = self.calculate_distance_between(closest_point_target)
        
        angle = self.calculate_angle_between(closest_point_target)
        vel = speed if (dist_to_closest >= speed) else int(dist_to_closest)
        new_target_dx = math.cos(math.radians(angle)) * vel
        new_target_dy = math.sin(math.radians(angle)) * vel
        new_target = Position(self.x + new_target_dx, self.y + new_target_dy)
        
        nearby_enems = [e for e in aux_list2
                        if self.calculate_distance_between(e) <= 2*constants.MAX_SPEED]

        t = self.navigate_iter(game_map, new_target, vel, 1, 60, nearby_enems, ignore_list=ignore_list)
        if t is None:
            vel = max(vel-2, 1)
            t = self.navigate_iter(game_map, new_target, vel, 3, 60, nearby_enems, ignore_list=ignore_list)
        if t is None:
            vel = max(vel-2, 1)
            t = self.navigate_iter(game_map, new_target, vel, 6, 60, nearby_enems, ignore_list=ignore_list)
        if t is None:
            return self.thrust(0, 0)
        else:
            return t

    def navigate_guardian(self, target, game_map, gstate, speed, avoid_obstacles=True,
                          max_corrections=90, angular_step=1, ignore_ships=False,
                          ignore_planets=False, aux_list=[]):
        '''

        '''
        closest_point_target = self.closest_point_to(target)
        dist_to_closest = self.calculate_distance_between(closest_point_target)

        angle = self.calculate_angle_between(closest_point_target)
        distance = speed if (dist_to_closest >= speed) else int(dist_to_closest)
        new_target_dx = math.cos(math.radians(angle))*distance
        new_target_dy = math.sin(math.radians(angle))*distance
        new_target = Position(self.x + new_target_dx, self.y + new_target_dy)

        vel = distance
        t = self.navigate_iter(game_map, new_target, vel, 3, 20)
        if t is None:
            vel = max(vel-2, 1)
            t = self.navigate_iter(game_map, new_target, vel, 6, 20)
        if t is None:
            vel = max(vel-2, 1)
            t = self.navigate_iter(game_map, new_target, vel, 18, 20)
        if t is None:
            return self.thrust(0, 0)
        else:
            return t

    def navigate_corner(self, target, game_map, gstate, speed, avoid_obstacles=True,
                       max_corrections=90, angular_step=1, ignore_ships=False,
                       ignore_planets=False, aux_list=[], aux_list2=[]):
        '''
        aux_list = undocked enemies
        '''
        closest_point_target = self.closest_point_to(target)
        dist_to_closest = self.calculate_distance_between(closest_point_target)

        angle = self.calculate_angle_between(closest_point_target)
        distance = speed if (dist_to_closest >= speed) else int(dist_to_closest)
        new_target_dx = math.cos(math.radians(angle)) * distance
        new_target_dy = math.sin(math.radians(angle)) * distance
        new_target = Position(self.x + new_target_dx, self.y + new_target_dy)

        #Find nearest enem ships
        nearby_enems = [e for e in gstate.undocked_enems
                        if self.calculate_distance_between(e) <= 5 + constants.MAX_SPEED]
        nearby_allies = [s for s in game_map.get_me().all_ships()
                         if (s.role == 1 or s.role == 2)
                         and self.calculate_distance_between(s) <= 5 + constants.MAX_SPEED]
        #if there are nearby enemies, and outnumbered, evade them
        if len(nearby_enems) >= len(nearby_allies):
            #add enemy thrust vectors to target vector
            #assume enemy thrusts toward my ship
            for e in nearby_enems:
                e_angl = e.calculate_angle_between(self)
                e_magn = constants.MAX_SPEED
                new_target = new_target + Position(math.cos(math.radians(e_angl))*e_magn,
                                                   math.sin(math.radians(e_angl))*e_magn)
            closest_point_target = self.closest_point_to(new_target)
            dist_to_closest = self.calculate_distance_between(closest_point_target)

            angle = self.calculate_angle_between(closest_point_target)
            vel = speed if (dist_to_closest >= speed) else int(dist_to_closest)
            new_target_dx = math.cos(math.radians(angle)) * vel
            new_target_dy = math.sin(math.radians(angle)) * vel
            new_target = Position(self.x + new_target_dx, self.y + new_target_dy)
            t = self.navigate_iter(game_map, new_target, vel, 3, 20)
            if t is None:
                t = self.navigate_iter(game_map, new_target, vel, 6, 20)
            if t is None:
                t = self.navigate_iter(game_map, new_target, vel, 18, 20)
            if t is None:
                return self.thrust(0, 0)
            else:
                return t
        #else attack docked enemies
        else:
            vel = distance
            t = self.navigate_iter(game_map, new_target, vel, 3, 20, aux_list=nearby_enems)
            if t is None:
                vel = max(vel-2, 1)
                t = self.navigate_iter(game_map, new_target, vel, 6, 20, aux_list=nearby_enems)
            if t is None:
                vel = max(vel-2, 1)
                t = self.navigate_iter(game_map, new_target, vel, 18, 20, aux_list=nearby_enems)
            if t is None:
                return self.thrust(0, 0)
            else:
                return t

    def navigate_flee(self, target, game_map, gstate, speed):
        '''
        aux_list = undocked enemies
        '''
        closest_point_target = self.closest_point_to(target)
        dist_to_closest = self.calculate_distance_between(closest_point_target)

        angle = self.calculate_angle_between(closest_point_target)
        distance = speed if (dist_to_closest >= speed) else int(dist_to_closest)
        new_target_dx = math.cos(math.radians(angle)) * distance
        new_target_dy = math.sin(math.radians(angle)) * distance
        new_target = Position(self.x + new_target_dx, self.y + new_target_dy)

        #Find nearest enem ships
        nearby_enems = [e for e in gstate.undocked_enems
                        if self.calculate_distance_between(e) <= 5 + constants.MAX_SPEED]
        nearby_allies = [s for s in game_map.get_me().all_ships()
                         if (s.role == 1 or s.role == 2)
                         and self.calculate_distance_between(s) <= 5 + constants.MAX_SPEED]
        #if there are nearby enemies, and outnumbered, evade them
        if nearby_enems and (len(nearby_enems) >= len(nearby_allies)):
            #add enemy thrust vectors to target vector
            #assume enemy thrusts toward my ship
            for e in nearby_enems:
                e_angl = e.calculate_angle_between(self)
                e_magn = constants.MAX_SPEED
                new_target = new_target + Position(math.cos(math.radians(e_angl))*e_magn,
                                                   math.sin(math.radians(e_angl))*e_magn)
            closest_point_target = self.closest_point_to(new_target)
            dist_to_closest = self.calculate_distance_between(closest_point_target)

            angle = self.calculate_angle_between(closest_point_target)
            vel = speed if (dist_to_closest >= speed) else int(dist_to_closest)
            new_target_dx = math.cos(math.radians(angle)) * vel
            new_target_dy = math.sin(math.radians(angle)) * vel
            new_target = Position(self.x + new_target_dx, self.y + new_target_dy)
            t = self.navigate_iter(game_map, new_target, vel, 3, 120)
            if t is None:
                return self.thrust(0, 0)
            else:
                return t
        #else attack docked enemies
        else:
            vel = distance
            t = self.navigate_iter(game_map, new_target, vel, 3, 120)
            if t is None:
                return self.thrust(0, 0)
            else:
                return t

    def thrust_overlap(self, gmap, thrust):
        '''
        Check if proposed thrust collides with previous commands
        '''
        for s in gmap.get_me().all_ships():
            #Need not look at self
            if s.id == self.id:
                continue
            #Need not look at distant ships
            if self.calculate_distance_between(s) > 2*constants.MAX_SPEED:
                continue
            #Need not look at stationary ships
            if s.thrust_cmd is None:
                continue
            x0, y0 = thrust.x0, thrust.y0
            vx0, vy0 = thrust.vx, thrust.vy

            x1, y1 = s.thrust_cmd.x0, s.thrust_cmd.y0
            vx1, vy1 = s.thrust_cmd.vx, s.thrust_cmd.vy
            for t in range(0, 23):
                dx = x0 - x1 + t*(vx0 - vx1)/20.
                dy = y0 - y1 + t*(vy0 - vy1)/20.
                r = math.sqrt(dx**2 + dy**2)
                if r <= 2.05*self.radius:
                    return True

        return False

    def evade_enems(self, gmap, thrust, enems=[]):
        '''
        Check if proposed thrust collides with enemy commands
        '''
        for e in enems:
            #Need not look at distant ships
            if self.calculate_distance_between(e) > 2*constants.MAX_SPEED:
                continue
            #Need not look at stationary ships
            if e.thrust_cmd is None:
                continue

            x0, y0 = thrust.x0, thrust.y0
            vx0, vy0 = thrust.vx, thrust.vy

            x1, y1 = e.thrust_cmd.x0, e.thrust_cmd.y0
            vx1, vy1 = e.thrust_cmd.vx, e.thrust_cmd.vy
            for t in range(0, 22):
                dx = x0 - x1 + t*(vx0 - vx1)/20.
                dy = y0 - y1 + t*(vy0 - vy1)/20.
                r = math.sqrt(dx**2 + dy**2)
                if r <= 2.05*e.radius:
                    return True

        return False

    def can_dock(self, planet):
        """
        Determine whether a ship can dock to a planet

        :param Planet planet: The planet wherein you wish to dock
        :return: True if can dock, False otherwise
        :rtype: bool
        """
        #return self.calculate_distance_between(planet) <= planet.radius + constants.DOCK_RADIUS
        return all([self.calculate_distance_between(planet) <= planet.radius + constants.DOCK_RADIUS,
                not planet.is_full()])

    def _link(self, players, planets):
        """
        This function serves to take the id values set in the parse function and use it to populate the ship
        owner and docked_ships params with the actual objects representing each, rather than IDs

        :param dict[int, game_map.Player] players: A dictionary of player objects keyed by id
        :param dict[int, Planet] players: A dictionary of planet objects keyed by id
        :return: nothing
        """
        self.owner = players.get(self.owner)  # All ships should have an owner. If not, this will just reset to None
        self.planet = planets.get(self.planet)  # If not will just reset to none

    @staticmethod
    def _parse_single(player_id, tokens):
        """
        Parse a single ship given tokenized input from the game environment.

        :param int player_id: The id of the player who controls the ships
        :param list[tokens]: The remaining tokens
        :return: The ship ID, ship object, and unused tokens.
        :rtype: int, Ship, list[str]
        """
        (sid, x, y, hp, vel_x, vel_y,
         docked, docked_planet, progress, cooldown, *remainder) = tokens

        sid = int(sid)
        docked = Ship.DockingStatus(int(docked))

        ship = Ship(player_id,
                    sid,
                    float(x), float(y),
                    int(hp),
                    float(vel_x), float(vel_y),
                    docked, int(docked_planet),
                    int(progress), int(cooldown))

        return sid, ship, remainder

    @staticmethod
    def _parse(player_id, tokens):
        """
        Parse ship data given a tokenized input.

        :param int player_id: The id of the player who owns the ships
        :param list[str] tokens: The tokenized input
        :return: The dict of Players and unused tokens.
        :rtype: (dict, list[str])
        """
        ships = {}
        num_ships, *remainder = tokens
        for _ in range(int(num_ships)):
            ship_id, ships[ship_id], remainder = Ship._parse_single(player_id, remainder)
        return ships, remainder

    def __str__(self):
        return "Entity {} (id: {}) at position: (x = {}, y = {}), with radius = {}"\
            .format(self.__class__.__name__, self.id, self.x, self.y, self.radius)


class Position(Entity):
    """
    A simple wrapper for a coordinate. Intended to be passed to some functions in place of a ship or planet.

    :ivar id: Unused
    :ivar x: The x-coordinate.
    :ivar y: The y-coordinate.
    :ivar radius: The position's radius (should be 0).
    :ivar health: Unused.
    :ivar owner: Unused.
    """

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 0
        self.health = None
        self.owner = None
        self.id = None

    def _link(self, players, planets):
        raise NotImplementedError("Position should not have link attributes.")

    def __add__(self, other):
        return Position(self.x + other.x, self.y + other.y)


class Thrust:
    '''
    Class for holding thrust info
    '''
    def __init__(self, ship, magnitude, angle):
        self.id = ship.id
        self.magnitude = int(magnitude)
        self.angle = angle
        self.vx = magnitude*math.cos(math.radians(self.angle))
        self.vy = magnitude*math.sin(math.radians(self.angle))
        self.x0 = ship.x
        self.y0 = ship.y
        self.x1 = ship.x + self.vx
        self.y1 = ship.y + self.vy

    def __str__(self):
        return "Thrust {} (ship id: {}) with: (magn = {}, angl = {})"\
            .format(self.__class__.__name__, self.id, self.magnitude, self.angle)

class Squadron:
    '''
    Class for grouping together attacking ships into co-moving squadrons
    '''
    def __init__(self, gstate, target_player_id, squad_id, ship_ids):
        self.gstate = gstate
        self.id = squad_id
        self.target_player_id = target_player_id
        self.ship_ids = ship_ids
        self.first_pass = 0
        self.second_pass = 0
        self.x = 0
        self.y = 0

        #set roles, remove ships from other state lists
        for sid in self.ship_ids:
            gstate.clean_ship(sid)
            gstate.set_ship_role(sid, 3)


    def form_squadron(self):
        '''
        set roles to squadron attacker (3)
        form up at central location with angle
        '''
        #establish target
        enems = self.gstate.gmap.get_player(self.target_player_id).all_ships()
        ship = self.gstate.gmap.get_me().get_ship(self.ship_ids[0])
        target = min(enems, key=ship.calculate_distance_between)

        cmds = []
        #left/right
        if (target.y < ship.y + 20) and (target.y > ship.y - 20):
            logging.warning('determined left/right config')
        #up/down
        else:
            logging.warning('determined up/down config')
            if self.first_pass == 0:
                if target.y < ship.y:
                    logging.info('detected down')
                    th = 180
                else:
                    th = 0
                #order ships by distance
                ships = [self.gstate.gmap.get_me().get_ship(sid) for sid in self.ship_ids]
                ships.sort(key=target.calculate_distance_between)
                ship1 = ships[0]
                ship2 = ships[1]
                ship3 = ships[2]
                self.ship_ids = [ship1.id, ship2.id, ship3.id]

                #ship one goes 4 units toward enemy
                cmds.append(ship1.thrust(4, 90+th))

                #ship two goes left
                cmds.append(ship2.thrust(7, 131.538+th))

                #ship three goes right
                cmds.append(ship3.thrust(5, 57.4493+th))

                self.first_pass = 1
            else:
                if target.y < ship.y:
                    logging.info('detected down')
                    th = 180
                else:
                    th = 0
                #order ships by distance
                ships = [self.gstate.gmap.get_me().get_ship(sid) for sid in self.ship_ids]
                ships.sort(key=target.calculate_distance_between)
                ship1 = ships[0]
                ship2 = ships[1]
                ship3 = ships[2]

                #ship one does nothing
                cmds.append(ship1.thrust(0, 90+th))

                #ship two goes down 7 unit
                cmds.append(ship2.thrust(4, 26.1099+th))

                #ship two goes down 7 unit
                cmds.append(ship3.thrust(6, 105.369+th))

                self.x = ship1.x
                self.y = ship1.y

                self.second_pass = 1
                logging.warning('Form up squadron')
        return cmds


    def navigate(self, undocked_enems):
        '''
        issue thrust commands to each ship
        '''
        if self.second_pass == 0:
            return self.form_squadron()
        else:
            #establish target
            enems = [e for e in self.gstate.gmap.get_player(self.target_player_id).all_ships()
                     if e.docking_status != Ship.DockingStatus.UNDOCKED]
            if not enems:
                enems = self.gstate.gmap.get_player(self.target_player_id).all_ships()

            #if enemy is eliminated, convert to miners
            if not enems:
                self.disband_squadron()
                logging.warning('squadron disband')
                return []
            else:
                #create a virtual ship to control the others
                ship = Ship(0, -1, self.x, self.y, 999, 0, 0,
                            Ship.DockingStatus.UNDOCKED, None, 0, 0)
                ship.role = 3
                ship.radius = 1.75
                target = min(enems, key=ship.calculate_distance_between)
                ships = [self.gstate.gmap.get_me().get_ship(sid) for sid in self.ship_ids]

            cmds = []
            #navigate furthest ship to target
            thrust = ship.navigate(
                target,
                self.gstate.gmap,
                self.gstate,
                speed=int(constants.MAX_SPEED),
                ignore_ships=False,
                ignore_planets=False,
                max_corrections=180,
                angular_step=3,
                aux_list=[],
                aux_list2=undocked_enems,
                ignore_list=ships)

            magn, angl = ship.thrust_cmd.magnitude, ship.thrust_cmd.angle
            self.x = self.x + math.cos(math.radians(angl))*magn
            self.y = self.y + math.sin(math.radians(angl))*magn
            for s in ships:
                cmds.append(s.thrust(magn, angl))
        return cmds

    def disband_squadron(self):
        '''
        reassign roles
        '''
        self.gstate.disband_squadron(self)
        self.ship_ids = []

    def add_member(self, ship):
        pass

    