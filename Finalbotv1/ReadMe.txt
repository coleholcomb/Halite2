Finalbot v1

Ported from Finalbot v0
Changes:
    Better early game

    TODO:
        Cleaner attacker movement (todo)
        More effective miner queueing 4p (todo)
        if production is higher than enemies, kamikaze on miners
        Miner undocking strategy/Cheese protection
        Attackers keep distance from enemies
        Protect miners more effectively
        Antichasing

Known Issues:
    Undercommiting to protecting miners?
    Too many self-collisions
    Too many collisions with enemies
    
Overall Strat:

    If planet contested, build only Attackers
    before turn 30 only miners, after 50/50

    2p: Preferentially capture the middle planets
    4p: Preferentially capture the planets close to the starting side.

    Miners: Queue to planets based on priority
            While avoiding enemy undocked ships
            attack enemy docked ships if p is owned by enemy
            else dock on planet, near other docked ships if possible

    Attackers: Attack nearest enemy, but try to group up to get number advantage

History:
Finalbot v1: Early game scattering
Finalbot v0: Better Miner Q-ing (assess_planets)
Focusbot v3: Attacker clustering adjustment
Focusbot v2: Early all-in counter strategy (commands.mine_step)
Focusbot v1: 4p corner retreat. Fixed squadron 3rd miner bug. Init miner Q-ing 4p. 
Focusbot v0: Init miner queueing. Better atck clustering. Better miner offense.
Guardianbot v4: Timeout protection. 2p/4p planet queueing strategy.
Guardianbot v3: Fixed squadron formation
Guardianbot v2: Miners attack docked enemies, evade all other enemies. 
                Attackers seek numbers advantage before fighting.
Guardianbot v1: Cleaned up navigation routine. Limited to ~60 iterations, favoring forward motion.
Guardianbot v0: Role assignment refactor. Guardian role implemented (but not perfected?)
Skullgridbot v7: Squadrons for early chees. Cluster around miners when under attack (bad).
Skullgridbot v6: Planet Queueing Efficiency. 2p/4p first turn strats.
Skullgridbot v5: strategy.py. All-In/Scaling first turn strats.
Skullgridbot v4: Implemented State framework. Storing ship roles.
Skullgridbot v3: Improved navigation (less dock bunching and avoid moving targets)
Skullgridbot v2: Planet priority from dist -> dist/radius
Skullgridbot v1
Skullgridbot v0
Nostalbot v2
