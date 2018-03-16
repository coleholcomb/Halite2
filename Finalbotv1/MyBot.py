#%%
import logging #logging module for print statements
import time #timer info
import random #random number generator
import numpy #for vectorized code (todo)

import hlt #interface with the Halite engine

# GAME START
game = hlt.Game("Finalbotv1") #Initialize game
state = hlt.state.State()
logging.info("Starting my Final bot!") #Init message

FIRST_TURN_FLAG = 1

while True:
    #Begin timer
    start = time.time()

    # TURN START
    # Update the map for the new turn
    start_up = time.time()
    game_map = game.update_map()
    state.update(game_map)
    end_up = time.time()
    logging.info('Map and State update: '+str(end_up-start_up))
    #if state.turn > 15:
    #    break

    #Issue commands to ships
    command_queue = []
    if FIRST_TURN_FLAG:
        hlt.strategy.first_turn(game_map, state)
        FIRST_TURN_FLAG = 0

    for cmd in hlt.commands.sqrn_step(state):
        command_queue.append(cmd)
    logging.info('MyBot: squadron commands')

    while (state.ships_guar or state.ships_atck
           or state.ships_mine or state.ships_corn
           or state.ships_flee):
        for cmd in hlt.commands.atck_step(game_map, state):
            command_queue.append(cmd)
        logging.info('MyBot: attacker commands')

        for cmd in hlt.commands.mine_step(game_map, state):
            command_queue.append(cmd)
        logging.info('MyBot: miner commands')

        for cmd in hlt.commands.guar_step(game_map, state):
            command_queue.append(cmd)
        logging.info('MyBot: guardian commands')

        for cmd in hlt.commands.corn_step(game_map, state):
            command_queue.append(cmd)
        logging.info('MyBot: corner commands')

        for cmd in hlt.commands.flee_step(game_map, state):
            command_queue.append(cmd)
        logging.info('MyBot: flee commands')

    #Complain about collisions
    # ships = game_map.get_me().all_ships()
    # while ships:
    #     ship = ships.pop()
    #     if ship.thrust_cmd:
    #         if ship.thrust_overlap(game_map, ship.thrust_cmd):
    #             logging.warning('Thrust collision! Ship '+str(ship.id))
    #         obst = game_map.obstacles_between(ship, hlt.entity.Position(ship.thrust_cmd.x1,
    #                                                                 ship.thrust_cmd.y1), ())
    #         if obst:
    #             logging.warning('Stationary collision! Ship '+str(ship.id)+' '+str(obst))

    # Send our set of commands to the Halite engine for this turn
    game.send_command_queue(command_queue)
    # TURN END

    #End timer
    end = time.time()
    logging.info('Turn length '+str(end-start))

# GAME END
