from typing import List, Dict
import re
import csv
from pathlib import Path
from json import loads, dumps


# Parser ecrit pour le tournoi BDA KSC. Version 6 (finale ++-)
# Parser wrote for the BDA KSC's tournament. Version 6 (final ++-)
# Todo : Gestion des équipes, approx dans le final tournament


def full_name_translator(f_n, team_play: bool):
    m = None
    if team_play:
        m = re.match(
            r'(?P<BDA>[^-]+)-(?P<stock_mod>[^-]+)-(?P<cat>[^-]+)-(?P<pseudo>[^-]+)-(?P<craft_name>.+)$', f_n)
    if m is None:
        m = re.match(
            r'(?P<BDA>[^-]+)-(?P<stock_mod>[^-]+)-(?P<cat>[^-]+)-(?P<pseudo>[^-]+)-(?P<craft_name>.+)_(?P<nbr>\d+)$', f_n)
    if m is None:
        m = re.match(r'(?P<BDA>[^-]+)-(?P<stock_mod>[^-]+)-(?P<cat>[^-]+)-(?P<pseudo>[^-]+)-(?P<craft_name>.+)$', f_n)
    if m is None:
        return 'NA', 'NA', 'NA', f_n
    stock_mod = m['stock_mod'].strip(' ')
    cat = m['cat'].strip(' ')
    pseudo = m['pseudo'].strip(' ')
    craft_name = m['craft_name'].strip(' ')
    return stock_mod, cat.upper(), pseudo, craft_name


class Config:
    def __init__(self, score_position, score_nbr_clean_k_b, score_nbr_clean_k_m, score_nbr_clean_k_r,
                 score_bullet_damages, score_missiles_damages, score_accuracy, score_ramming,
                 score_parts_destructed_by_ram, score_dead_time, heats_round):
        self.score_position = score_position
        self.score_nbr_clean_k_b = score_nbr_clean_k_b
        self.score_nbr_clean_k_m = score_nbr_clean_k_m
        self.score_nbr_clean_k_r = score_nbr_clean_k_r
        self.score_bullet_damages = score_bullet_damages
        self.score_missiles_damages = score_missiles_damages
        self.score_accuracy = score_accuracy
        self.score_ramming = score_ramming
        self.heats_round = heats_round
        self.score_parts_destructed_by_ram = score_parts_destructed_by_ram
        self.score_dead_time = score_dead_time
        self.path = Path()
        self.have_teams = False

    def __str__(self):
        titles = ['score_position', 'score_nbr_clean_k_b', 'score_nbr_clean_k_m', 'score_nbr_clean_k_r',
                  'score_bullet_damages', 'score_missiles_damages', 'score_accurac', 'score_ramming',
                  'score_parts_destructed_by_ram', 'score_dead_time', 'heats_round']
        values = [self.score_position, self.score_nbr_clean_k_b, self.score_nbr_clean_k_m, self.score_nbr_clean_k_r,
                  self.score_bullet_damages, self.score_missiles_damages, self.score_accuracy, self.score_ramming,
                  self.score_parts_destructed_by_ram, self.score_dead_time, self.heats_round]
        aff = 'Config :\n'
        for i in range(min(len(titles), len(values))):
            aff += f'{titles[i]} : {values[i]}\n'
        return aff


class Section:
    def __init__(self, avions):
        self.avions = avions
        self.table = []
        self.duree = 0
        self.date = ''

    def tri_avions(self, tri, configs):
        for av in self.avions.values():
            n_table = []
            nbr_avions = len(self.table)
            for i in range(nbr_avions):
                ele = self.table[i]
                if tri:
                    av.f_score(configs, self.duree)
                    ele.f_score(configs, self.duree)
                if ele.score < av.score:
                    n_table.append(ele)
                else:
                    n_table.append(av)
                    n_table.extend(self.table[i:])
                    break
            else:
                n_table.append(av)
            self.table = n_table

        for i in range(len(self.table)):
            self.table[i].podium = len(self.table) - i
        self.table.reverse()
        return self.table

    def add_duree(self, value):
        self.duree += value


class Heat(Section):
    def __init__(self, duree, date, round_n, avions: dict):
        Section.__init__(self, avions)
        self.duree = duree
        self.date = date
        self.round = round_n
        self.avions = avions


class Round(Section):
    def __init__(self, avions, lst_heats):
        Section.__init__(self, avions)
        self.heats = lst_heats

    def add_avion(self, lgn, full_name, team_play: bool):
        if full_name in self.avions:
            self.avions = add_values(self.avions, full_name, lgn)
        else:
            avion = create_avion(full_name, lgn, team_play)
            self.avions[full_name] = avion

    def have_avion(self, full_name):
        return full_name in self.avions


class Tournoi(Section):
    def __init__(self, avions, lst_rounds):
        Section.__init__(self, avions)
        self.lst_rounds = lst_rounds


class Avion:
    def __init__(self, full_name,
                 nbr_shot_m, missiles_damages, clean_kill_m,
                 nbr_shot_b, bullets_damages, clean_kill_b,
                 fired, touched,
                 nbr_ram, parts_destructed_by_ram, clean_kill_ram,
                 position, score, podium, team_play):
        self.stock_mod, self.cat, self.joueur, self.craft_name = full_name_translator(full_name, team_play)
        self.full_name = full_name
        self.nbr_shot_b = nbr_shot_b
        self.nbr_shot_m = nbr_shot_m
        self.nbr_ram = nbr_ram
        self.fired = fired
        self.touched = touched
        self.bullets_damages = bullets_damages
        self.missiles_damages = missiles_damages
        self.death_order = position
        self.podium = podium
        self.dead_time = -1
        self.score = score
        self.nbr_clean_k_b = clean_kill_b
        self.nbr_clean_k_m = clean_kill_m
        self.nbr_clean_k_ram = clean_kill_ram
        self.clean_kill_b = set()
        self.clean_kill_m = set()
        self.clean_kill_r = set()
        self.parts_destructed_by_ram = parts_destructed_by_ram
        self.equipe = None
        self.alive = False

    def __str__(self):
        return f'Avion({self.full_name}, {self.nbr_ram}, {self.nbr_clean_k_ram})'

    def change_accuracy(self, touched, fired):
        self.fired = fired
        self.touched = touched

    def add_accuracy(self, touched, fired):
        self.fired += fired
        self.touched += touched

    def add_shot_b(self, nbr):
        self.nbr_shot_b += nbr

    def add_shot_m(self, nbr):
        self.nbr_shot_m += nbr

    def add_clean_k_b(self, value):
        self.clean_kill_b.add(value)

    def add_clean_k_m(self, value):
        self.clean_kill_m.add(value)

    def add_clean_k_r(self, value):
        self.clean_kill_r.add(value)

    def add_nbr_c_k_b(self, value):
        self.nbr_clean_k_b += value

    def add_nbr_c_k_m(self, value):
        self.nbr_clean_k_m += value

    def add_nbr_c_k_r(self, value):
        self.nbr_clean_k_ram += value

    def add_ram(self, value):
        self.nbr_ram += value

    def add_b_damages(self, value):
        self.bullets_damages += value

    def add_m_damages(self, value):
        self.missiles_damages += value

    def f_nbr_clean_count(self):
        print('Recalculllation')
        self.nbr_clean_k_b = len(self.clean_kill_b)
        self.nbr_clean_k_m = len(self.clean_kill_m)
        self.nbr_clean_k_ram = len(self.clean_kill_r)

    def f_score(self, configs, duree):
        if self.cat in configs:
            config = configs[self.cat]
        else:
            config = configs['#ALL']
        self.f_nbr_clean_count()
        if self.fired == 0:
            acc = 0
        else:
            acc = self.touched / self.fired
        if self.dead_time == -1:
            self.dead_time = duree
        self.score = self.death_order * config.score_position + self.nbr_clean_k_b * config.score_nbr_clean_k_b
        self.score += self.nbr_clean_k_m * config.score_nbr_clean_k_m + self.nbr_clean_k_ram * config.score_nbr_clean_k_r
        self.score += self.bullets_damages * config.score_bullet_damages
        self.score += self.missiles_damages * config.score_missiles_damages + acc * config.score_accuracy
        self.score += self.nbr_ram * config.score_ramming + self.parts_destructed_by_ram * config.score_parts_destructed_by_ram
        self.score += self.dead_time * config.score_dead_time
        #  print('score', self.score, self.parts_destructed_by_ram, self.parts_destructed_by_ram * config.score_parts_destructed_by_ram)
        return self.score

    def add_score(self, value):
        self.score += value

    def add_position(self, value):
        """WTF"""
        self.death_order += int(value)

    def add_parts_destructed_by_ram(self, value):
        self.parts_destructed_by_ram += value


class Equipe:
    def __init__(self, nom: str, avions_de_lequipe: List[Avion], result: str):
        m = re.match(r'.+/(?P<nom>[^/]+)$', nom)
        if m is None:
            self.nom = nom
        else:
            self.nom = m['nom']
        self.avions_de_lequipe = avions_de_lequipe
        self.result = result
        self.avion = None

    def assign_team_for_planes(self):
        for pla in self.avions_de_lequipe:
            pla.equipe = self.nom

    def plane_creator(self):
        self.avion = Avion('A-B-C-D-E', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        self.avion.equipe = self.nom
        for av in self.avions_de_lequipe:
            self.avion.fired += av.fired
            self.avion.touched += av.touched
            self.avion.bullets_damages += av.bullets_damages
            self.avion.missiles_damages += av.missiles_damages
            self.avion.nbr_shot_b += av.nbr_shot_b
            self.avion.nbr_shot_m += av.nbr_shot_m
            self.avion.nbr_ram += av.nbr_ram
            self.avion.death_order += av.death_order
            self.avion.podium += av.podium
            self.avion.dead_time += av.dead_time
            self.avion.score += av.score
            self.avion.nbr_clean_k_b += av.nbr_clean_k_b
            self.avion.nbr_clean_k_m += av.nbr_clean_k_m
            self.avion.nbr_clean_k_ram += av.nbr_clean_k_ram
            self.avion.parts_destructed_by_ram += av.parts_destructed_by_ram
        print('s', self.avion.nbr_clean_k_b)

    def calculate_scoring(self):
        a = 0
        for avion in self.avions_de_lequipe:
            a += avion.alive
        return a


def prem_lgn(lgn: str):
    m = re.match(r'\[[^:]*:(?P<tag>\d+)]: '
                 r'Dumping Results after (?P<duration>\d+)s at '
                 r'(?P<date>\d{4}-\d{2}-\d{2}) (?P<hour>\d{2}:\d{2}:\d{2}) [+-]\d{2}:\d{2}$', lgn)
    if m is None:
        m = re.match(r'\[[^:]*:(?P<tag>\d+)]: '
                     r'Dumping Results after (?P<duration>\d+)s (?P<truc>.+) at '
                     r'(?P<date>\d{4}-\d{2}-\d{2}) (?P<hour>\d{2}:\d{2}:\d{2}) [+-]\d{2}:\d{2}$', lgn)
    elif m is None:
        print('m est None, la premiere ligne a un probleme.')  # m is None, the first line is not ok
        return 0, 0, '00-00-00', '00:00:00'
    tag = int(m['tag'])
    duration = int(m['duration'])
    date = m['date']
    hour = m['hour']
    return tag, duration, date, hour


def match_regular_lgn(lgn):
    cat = ''
    event = ''
    if lgn != '':
        m = re.match(r'\[.+]: (?P<cat>[A-Z]+):', lgn)
        cat = m['cat']
        last_carac = m.end()
        event = lgn[last_carac:]
    return cat, event


def log(lgn_p_lgn: List[str], avions: Dict[str, Avion], team_play: bool):
    def multi_participant(text):
        def multi_participant_rec(text):
            nbrs = []
            killers = []
            m = re.match(r'(?P<somethings>.+):(?P<nbr>[^:]+):(?P<killer>.+)$', text)
            if m is None:
                m = re.match(r'(?P<nbr>[^:]+):(?P<killer>.+)$', text)
            else:
                k, n = multi_participant_rec(m['somethings'])
                killers.extend(k)
                nbrs.extend(n)
            nbrs.append(float(m['nbr']))
            killers.append(m['killer'])
            return killers, nbrs

        m = re.match(r'(?P<victim>[^:]+):(?P<somethings>.+):(?P<nbr>[^:]+):(?P<killer>.+)$', text)
        if m is None:
            m = re.match(r'(?P<victim>[^:]+):(?P<nbr>[^:]+):(?P<killer>.+)$', text)
            victim = m['victim']
            nbrs = [float(m['nbr'])]
            killers = [m['killer']]
        else:
            victim = m['victim']
            killers, nbrs = multi_participant_rec(m['somethings'])
            killers.append(m['killer'])
            nbrs.append(float(m['nbr']))
        return victim, killers, nbrs

    def new_avion(name, d_t):
        av = Avion(name, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, team_play)
        av.dead_time = d_t
        # print('new plane', name, d_t)
        return av

    def alive(text):
        avions[text].dead_time = -1
        avions[text].death_order = -1
        avions[text].alive = True

    def dead(text):
        m = re.match(r'(?P<death_order>\d+):(?P<s>\d+).(?P<ds>\d+):(?P<name>.*)$', text)
        avions[m['name']].dead_time = int(m['s']) + int(m['ds']) * 0.1
        avions[m['name']].death_order = int(m['death_order']) + 1

    def mia(text):
        """I don't understand"""
        m = re.match(r'(?P<name>.*)$', text)
        avions[m['name']].dead_time = -2

    def result(text):
        m = re.match(r'(?P<result>[^:]+):(?P<team>.+)$', text)
        # print(text)
        team_text = loads(m['team'])
        planes = []
        # print(team_text, type(team_text))
        if type(team_text) == dict:
            for name_plane in team_text['members']:
                if name_plane not in avions:
                    avions[name_plane] = new_avion(name_plane, -4)
                    planes.append(avions[name_plane])
            teams.append(Equipe(team_text['team'], planes, m['result']))
            return
        for dictionnary in team_text:
            planes = []
            for name_plane in dictionnary['members']:
                if name_plane not in avions:
                    avions[name_plane] = new_avion(name_plane, -4)
                    planes.append(avions[name_plane])
            teams.append(Equipe(dictionnary['team'], planes, m['result']))

    def deadteams(text):
        list_team = loads(text)  # It look like json
        for team_text in list_team:
            planes = []
            for name_plane in team_text['members']:
                if name_plane not in avions:
                    avions[name_plane] = new_avion(name_plane, -3)
                    planes.append(avions[name_plane])
            teams.append(Equipe(team_text['team'], planes, 'dead'))
            # print(team_text['team'], planes)

    def accuracy(text):
        """return 2 values: bullets fired and touched"""
        m = re.match(r'(?P<name>[^:]+):(?P<a>\d+)/(?P<b>\d+)', text)
        name = m['name']
        a = int(m['a'])
        b = int(m['b'])
        return name, (a, b)

    def wshotwb(text, avions):
        victim, killers, nbrs = multi_participant(text)
        for k in killers:
            avions[k].add_shot_b(1)
        return avions

    def wshotwm(text, avions):
        victim, killers, nbrs = multi_participant(text)
        for k in killers:
            avions[k].add_shot_m(1)
        return avions

    def wdomagew_b(text, avions):
        victim, killers, nbrs = multi_participant(text)
        for i, k in enumerate(killers):
            avions[k].add_b_damages(nbrs[i])
        return avions

    def wdomagew_m(text, avions):
        victim, killers, nbrs = multi_participant(text)
        for i, k in enumerate(killers):
            avions[k].add_m_damages(nbrs[i])
        return avions

    def wrammedw(text, avions):
        victim, killers, nbrs = multi_participant(text)
        for i, k in enumerate(killers):
            avions[k].add_ram(1)
            avions[k].add_parts_destructed_by_ram(int(nbrs[i]))
        return avions

    def clean_k_m(text):
        m = re.match(r'(?P<victim>[^:]+):(?P<killer>.+)$', text)
        victim = m['victim']
        killer = m['killer']
        return killer, victim

    def clean_k_b(text):
        m = re.match(r'(?P<victim>[^:]+):(?P<killer>.+)$', text)
        victim = m['victim']
        killer = m['killer']
        return killer, victim

    def clean_ram(text):
        m = re.match(r'(?P<victim>[^:]+):(?P<killer>.+)$', text)
        victim = m['victim']
        killer = m['killer']
        return killer, victim

    teams = []
    for lgn in lgn_p_lgn[1:]:
        cat, event = match_regular_lgn(lgn)
        if cat == 'ALIVE':
            if event[:7] not in ('Débris', 'DÃ©bris') and event[-5:] not in ('Avion', 'avion'):
                alive(event)
        elif cat == 'DEAD':
            dead(event)
        elif cat == 'MIA':
            mia(event)
        elif cat == 'ACCURACY':
            key, acc = accuracy(event)
            avions[key].change_accuracy(acc[0], acc[1])
        elif cat == 'WHOHITWHOWITHMISSILES':
            avions = wshotwm(event, avions)
        elif cat == 'WHOSHOTWHO':
            avions = wshotwb(event, avions)
        elif cat == 'WHODAMAGEDWHOWITHBULLETS':
            avions = wdomagew_b(event, avions)
        elif cat == 'WHODAMAGEDWHOWITHMISSILES':
            avions = wdomagew_m(event, avions)
        elif cat == 'WHORAMMEDWHO':
            avions = wrammedw(event, avions)
        elif cat == 'CLEANKILL':
            killer, victim = clean_k_b(event)
            avions[killer].add_clean_k_b(victim)
        elif cat == 'CLEANMISSILEKILL':
            killer, victim = clean_k_m(event)
            avions[killer].add_clean_k_m(victim)
        elif cat == 'CLEANRAM':
            killer, victim = clean_ram(event)
            avions[killer].add_clean_k_r(victim)
        elif cat == 'RESULT':
            result(event)
        elif cat == 'DEADTEAMS':
            deadteams(event)
    for team in teams:
        team.assign_team_for_planes()
    max_death_order = 0
    # print(avions)
    for avion in avions.values():
        # print(avion)
        max_death_order = max(avion.death_order, max_death_order)
    for avion in avions.values():
        if avion.death_order == -1:
            avion.death_order = max_death_order + 1
    return avions, teams


def values_table(avion):
    if avion.fired == 0:
        return 0
    return avion.touched / avion.fired


def table_maker(p, name, table: List[Avion], recalculate, configs, date, duree, team_play: bool, values):
    """0 stock_mod, 1joueur, 2categorie, 3nom_du_craft, 4nbr_shot_missiles, 5nbr_shot_bullets, 6missiles_dommages, 7bullets_dommages, 8clean_kill_missiles, 9clean_kill_bullets, 10fired, 11touched, 12accuracy, 13score, 14death_position"""
    round_table = []
    name = p / Path(name)
    with name.open(mode='w') as classement:
        table_writer = csv.writer(classement, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL, dialect='unix')
        table_heading = ['Stock/Mod', 'Categorie', 'Equipe', 'Joueur', 'Nom_Du_Craft',
                         'Nb_Shot_Missiles', 'Missiles_damages', 'CleanKillMissiles',
                         'Nb_Shot_Bullets', 'Bullets_damages', 'CleanKillBullets',
                         'Balles tirees', 'Balles touches', '%Accuracy',
                         'Nb_Ram', 'Parts_rammed', 'CleanKillRam',
                         'DeathOrder', 'Dead_Time', 'Score', 'Podium']
        if team_play:
            table_heading.pop(19)
            table_heading[4] = '%alive'
            table_heading.pop(3)
            table_heading.pop(1)
            table_heading.pop(0)
        table_writer.writerow(table_heading)
        round_table.append(table_heading)
        for y, avion in enumerate(table):
            acc = values_table(avion)
            if recalculate:
                avion.f_score(configs, duree)
                table_m = 'm1'
            else:
                table_m = 'm2'
            if team_play:
                t = [avion.equipe, round(values[avion.equipe][1]/values[avion.equipe][0]*100, 3),
                     avion.nbr_shot_m, avion.missiles_damages, avion.nbr_clean_k_m,
                     avion.nbr_shot_b, avion.bullets_damages, avion.nbr_clean_k_b,
                     avion.fired, avion.touched, round(acc*100, 3),
                     avion.nbr_ram, avion.parts_destructed_by_ram, avion.nbr_clean_k_ram,
                     avion.death_order, avion.dead_time, avion.podium]
            else:
                t = [avion.stock_mod, avion.cat, avion.equipe, avion.joueur, avion.craft_name,
                     avion.nbr_shot_m, avion.missiles_damages, avion.nbr_clean_k_m,
                     avion.nbr_shot_b, avion.bullets_damages, avion.nbr_clean_k_b,
                     avion.fired, avion.touched, round(acc*100, 3),
                     avion.nbr_ram, avion.parts_destructed_by_ram, avion.nbr_clean_k_ram,
                     avion.death_order, avion.dead_time, round(avion.score, 3), avion.podium]
            if y == 0:
                t.extend(['date (year/mo/da)', date])
            if y == 1:
                t.extend(['duree (s)', duree])
            table_writer.writerow(t)
            round_table.append(t)
            print(table_m, t)
    return round_table


def parametres_1():
    reponse = input('Choisissez un type de combat\n'
                    '[1] Normal\n'
                    '[2] BMB FHT\n'
                    '[3] Ramming\n\n'
                    'Reponse :')

    configs = [{'#ALL': Config(1, 2, 0.5, 1, 0.0002, 0.00002, 0, 2, 0, 0, True)},
               {'#ALL': Config(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, True),
                'FHT': Config(0, 1, 0, 1, 0.0005, 0, 1, 0.5, 0.5, 0.001, True),
                'BMB': Config(0, 1, 0, 1, 0.001, 0, 2, 0.5, 0.5, 0.005, True)},
               {'#ALL': Config(1, 0, 0, 10, 0, 0, 0, 5, 0.2, 0, True)}]
    configs = configs[int(reponse) - 1]
    config = configs['#ALL']
    infos = [config.score_position, config.score_nbr_clean_k_b, config.score_nbr_clean_k_m, config.score_nbr_clean_k_r,
             config.score_bullet_damages,
             config.score_missiles_damages, config.score_accuracy, config.score_ramming,
             config.score_parts_destructed_by_ram, config.heats_round]
    noms = ['score_position', 'score_nbr_clean_k_b', 'score_nbr_clean_k_m', 'score_nbr_clean_k_r',
            'score_bullet_damages',
            'score_missiles_damages', 'score_accuracy', 'score_ramming', 'score_parts_destructed_ny_ram', 'heats_round']
    print('\n\n')
    for i in range(len(noms)):
        print(noms[i], infos[i])
    input(str(config) + '\nOk ?')
    print('\n\n')
    return configs


def parametres_2(configs):
    config = configs['#ALL']
    infos = [config.score_position, config.score_nbr_clean_k_b, config.score_nbr_clean_k_m, config.score_nbr_clean_k_r,
             config.score_bullet_damages,
             config.score_missiles_damages, config.score_accuracy, config.score_ramming, config.heats_round]
    noms = ['score_position', 'score_nbr_clean_k_b', 'score_nbr_clean_k_m', 'score_nbr_clean_k_r',
            'score_bullet_damages',
            'score_missiles_damages', 'score_accuracy', 'score_ramming', 'heats_round']
    boolean_reponse = [False, False, False, False, False, False, False, True]
    resultats = infos[:]
    print('[n] pour ne pas changer la valeur, [nombre_reel] pour changer la valeur.\n'
          '[nom_du_parametre] [valeur_du_parametre]:[n ou reel]')
    for i in range(len(infos)):
        reponse = input(f'{noms[i]} {infos[i]}:')
        if reponse != 'n':
            if boolean_reponse[i]:
                resultats[i] = 'True' == reponse
            else:
                resultats[i] = float(reponse)
    print('\nresultats :', resultats, '\n\n\n')
    config.score_position = resultats[0]
    config.score_nbr_clean_k_b = resultats[1]
    config.score_nbr_clean_k_m = resultats[2]
    config.score_bullet_damages = resultats[3]
    config.score_missiles_damages = resultats[4]
    config.score_accuracy = resultats[5]
    config.score_ramming = resultats[6]
    config.heats_round = resultats[7]
    return {'#ALL': config}


def menu(p, configs):
    """
    :return: renvoie si l'on veut refaire les heat.csv
    """
    print(f"Current directory: {p.cwd()}")
    rep = ''
    while rep not in ('1', '2'):
        if rep == '3':
            configs = parametres_1()
        if rep == '4':
            configs = parametres_2(configs)
        rep = input(' _   _   _   _  ___  _\n'
                    '|_| |_| |   |    |  |_| |/\n'
                    '|   | | |_  |_   |  | | |\\ par harpercix et la communauté francophone\n\n'
                    'Parser, Analyser de logs, Calculateur de score et Créateur de tableaux pour Tournois de combats Aériens dans KSP.\n\n'
                    'Notes :\n'
                    '-Pensez bien à fermer les csv avant de relancer PACCTAK\n'
                    '-Possible de configurer PACCTAK a l\'interieur ou avec "pacctak_config.txt"\n'
                    '-Capable de s\'adapter à la nomenclature BDA-[Stock/Mods]-[Categorie]-[Pseudo]-[nom du craft]\n\n'
                    '[1] : tout mettre à jour [choix de base]\n'
                    '[2] : mettre à jour tout sauf les heats\n'
                    '[3] : choisir un scoring preconfigure\n'
                    '[4] : configurer ou modifier le scoring\n\n\n'
                    'Reponse : ')
    return configs, rep == '1'


def name_creator(stock_mod, joueur, categorie, nom_du_craft):
    return f'BDA-{stock_mod}-{joueur}-{categorie}-{nom_du_craft}'


def info_lat_heats_round(x, y, lgn, round_b):
    if not round_b:
        if y == 0:
            lgn.extend(['Heat', f'{x}'])
    elif round_b:
        if y == 0:
            lgn.extend(['Round', f'{x}'])
    if y == 0:
        lgn = ['CsvOrder'] + lgn
    else:
        lgn = [y] + lgn
    return lgn


def info_lat_glob(x, y, lgn, l_csv_g, nom, nbr_heats, nbr_rounds):
    m = re.match(r'Tournament (?P<nbrs>.+)$', nom)
    nbrs = m['nbrs']
    if y == 0 and x == l_csv_g - 1:
        lgn.extend(['Tournament', nbrs])
    if y == 0:
        lgn = ['CsvOrder'] + lgn
    else:
        lgn = [y] + lgn
    if y == 3 and x == l_csv_g - 1:
        lgn.extend(['Heats', nbr_heats])
    elif y == 4 and x == l_csv_g - 1:
        lgn.extend(['Rounds', nbr_rounds])
    return lgn


def add_values(avions, full_name, lgn):
    # 0, 1, 3, 4 : full_name
    avions[full_name].add_shot_m(int(lgn[5]))
    avions[full_name].add_m_damages(float(lgn[6]))
    avions[full_name].add_nbr_c_k_m(int(lgn[7]))
    avions[full_name].add_shot_b(int(lgn[8]))
    avions[full_name].add_b_damages(float(lgn[9]))
    avions[full_name].add_nbr_c_k_b(int(lgn[10]))
    avions[full_name].add_accuracy(int(lgn[12]), int(lgn[11]))
    # jump accuracy
    avions[full_name].add_ram(int(lgn[14]))
    avions[full_name].add_parts_destructed_by_ram(int(lgn[15]))
    avions[full_name].add_nbr_c_k_r(int(lgn[16]))
    avions[full_name].dead_time += float(lgn[18])
    avions[full_name].add_position(int(lgn[17]))
    avions[full_name].add_score(float(lgn[19]))
    # jump podium
    return avions


def team_points(p, teams: List[Equipe]):
    print('t', teams)
    values = {}
    for f in p.iterdir():
        filename = f.name
        if filename == 'teams.json':
            text = ''
            with f.open('r') as file:
                for line in file:
                    text += line
            values = loads(text)
            break
    for team in teams:
        if team.nom in values:
            values[team.nom][0] += len(team.avions_de_lequipe)
            values[team.nom][1] += team.calculate_scoring()
        else:
            values[team.nom] = (len(team.avions_de_lequipe), team.calculate_scoring())
    with (p/'teams.json').open('w') as file:
        file.write(dumps(values))


def heat_f(p, configs: Dict[str, Config]):
    csv_round = []
    heats = []
    print('\n--HEAT--')
    for f in p.iterdir():
        filename = f.name
        if filename[:5] == 'Round':
            for f2 in f.iterdir():
                if str(f2)[-4:] != '.log':
                    continue
                avions = {}
                m = re.match(r'Round (?P<nbr>\d+)$', filename)
                nbr_round = int(m['nbr'])
                while len(heats) - 1 < nbr_round:
                    heats.append([])
                with f2.open('r') as file:
                    heat_log = file.read().split('\n')
                    tag, duration, date, hour = prem_lgn(heat_log[0])
                    avions, teams = log(heat_log, avions, configs['#ALL'].have_teams)
                    teams_name = []
                    if not configs['#ALL'].have_teams:
                        for avion in avions.values():
                            if avion.equipe in teams_name:
                                for config in configs.values():
                                    config.have_teams = True
                                heat_f(p, configs)
                                return
                            teams_name.append(avion.equipe)
                    team_points(p, teams)
                    heat = Heat(duration, date, nbr_round, avions)
                    heats[nbr_round].append(heat)
                    print(f'{tag} :')
                    while nbr_round > len(csv_round) - 1:
                        csv_round.append([])
                    csv_round[nbr_round].append(
                        table_maker(p, f'{tag}_{nbr_round}.csv', heat.tri_avions(True, configs), True, configs,
                                    heat.date,
                                    heat.duree, False, None))


def create_avion(full_name, lgn, team_play):
    avion = Avion(full_name,
                  int(lgn[5]),
                  float(lgn[6]),
                  int(lgn[7]),
                  int(lgn[8]),
                  float(lgn[9]),
                  int(lgn[10]),
                  int(lgn[11]),
                  int(lgn[12]),
                  int(lgn[14]),
                  int(lgn[15]),
                  int(lgn[16]),
                  int(lgn[17]),
                  float(lgn[19]),
                  int(lgn[20]),
                  team_play)
    avion.dead_time = float(lgn[18])
    avion.equipe = lgn[2]
    return avion


def round_f(p, configs):
    rounds = []
    heats = []
    csv_round = []
    print('\n--ROUND--')
    for f in p.iterdir():
        tableau = []
        filename = f.name
        m = re.match(r'(?P<heat>\d+)_(?P<nbr_r>\d+)\.csv$', filename)
        if m is not None:
            nbr_r = int(m['nbr_r'])
            with f.open() as heat_log:
                h_reader = csv.reader(heat_log)
                for lgn in h_reader:
                    tableau.append(lgn)
            avions = {}
            for y, lgn in enumerate(tableau[1:]):
                full_name = name_creator(lgn[0], lgn[1], lgn[3], lgn[4])
                if full_name not in avions:
                    avion = create_avion(full_name, lgn, configs['#ALL'].have_teams)
                    avions[full_name] = avion
                else:
                    avions = add_values(avions, full_name, lgn)
            while len(heats) - 1 < nbr_r:
                heats.append([])
            heats[nbr_r].append(Heat(0, 0, nbr_r, avions))
            while nbr_r > len(csv_round) - 1:
                csv_round.append([])
            csv_round[nbr_r].append(tableau)
    for f in p.iterdir():
        filename = f.name
        m = re.match(r'(?P<heat>\d{8})_(?P<nbr_r>\d+).csv$', filename)
        if m is not None:
            nbr_r = int(m['nbr_r'])
            duree = 0
            date = ''
            tableau = []
            with f.open() as heat_log:
                h_reader = csv.reader(heat_log)
                for lgn in h_reader:
                    tableau.append(lgn)
            y = 0
            for lgn in tableau[1:]:
                while len(rounds) - 1 < nbr_r:
                    rounds.append(None)
                full_name = name_creator(lgn[0], lgn[1], lgn[3], lgn[4])
                if y == 0:
                    date = lgn[22]
                if y == 1:
                    duree += float(lgn[22])
                if rounds[nbr_r] is None:
                    """0nom_entié, 1nbr_shot_missiles, 2nbr_shot_bullets, 3nbr_ram, 4missiles_dommages, 5bullets_dommages, 6clean_kill_missiles, 7clean_kill_bullets, 8parts_destructed_by_ram, 9touched, 10fired, 11score, 12position, 13podium"""
                    avion = create_avion(full_name, lgn, configs['#ALL'].have_teams)
                    rounds[nbr_r] = Round({full_name: avion}, heats[nbr_r])
                else:
                    rounds[nbr_r].add_avion(lgn, full_name, configs['#ALL'].have_teams)
                rounds[nbr_r].date = date
                rounds[nbr_r].duree = duree
                y += 1
    csv_global = []
    for test_round in rounds:
        teams = []
        for avion in test_round.avions.values():
            if avion.equipe in teams:
                break
            teams.append(avion.equipe)
        else:
            break
    else:
        for config in configs.values():
            config.team = True
    for i, round_heats in enumerate(rounds):
        print(f'round {i} :')
        csv_global.append(table_maker(p, f'round_{i}.csv', round_heats.tri_avions(False, configs), False, configs,
                                      round_heats.date, round_heats.duree, False, None))
        if configs['#ALL'].heats_round:
            with open(p / f'heats round {i}.csv', mode='w') as table_round:
                table_writer = csv.writer(table_round, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL,
                                          dialect='unix')
                for x in range(len(csv_round[i])):
                    table = csv_round[i][x]
                    y = 0
                    for lgn in table:
                        lgn = info_lat_heats_round(x, y, lgn, False)
                        table_writer.writerow(lgn)
                        y += 1
                    table_writer.writerow([])
                for x in range(len(csv_global[i])):
                    lgn = info_lat_heats_round(i, x, csv_global[i][x], True)
                    table_writer.writerow(lgn)
    return rounds, csv_global


def team_f(p, avions, configs, date, duree):
    teams = {}
    for avion in avions.values():
        if avion.equipe in teams:
            teams[avion.equipe].avions_de_lequipe.append(avion)
        else:
            teams[avion.equipe] = Equipe(avion.equipe, [avion], 'None')
    avions_teams = []
    for team in teams.values():
        team.plane_creator()
    with open(p/'teams.json', 'r') as file:
        txt = ''
        for line in file:
            txt += line
        values = loads(txt)
    pourcentalive = []
    for e, v in values.items():
        pourcentalive.append((v[1] / v[0], e))
    pourcentalive.sort(key=lambda x: x[0], reverse=True)
    for i, po in enumerate(pourcentalive):
        teams[po[1]].avion.podium = i+1
        avions_teams.append(teams[po[1]].avion)
    table_maker(p, f'team tournament.csv', avions_teams, False, configs, date, duree, True, values)
    (p/'teams.json').unlink()


def tournament_f(p, csv_global, rounds, configs):
    print('\n--TOURNOI--')
    avions = {}
    duree = 0
    date = ''
    nbr_round = 0
    for f in p.iterdir():
        filename = f.name
        if 11 <= len(filename) <= 12 and f.suffix == '.csv' and filename[:6] == 'round_':
            nbr_round += 1
            tableau = []
            with f.open() as round_csv:
                r_reader = csv.reader(round_csv)
                for lgn in r_reader:
                    tableau.append(lgn)
            y = 0
            for lgn in tableau[1:]:
                full_name = name_creator(lgn[0], lgn[1], lgn[3], lgn[4])
                if y == 0:
                    date = lgn[22]
                elif y == 1:
                    duree += float(lgn[22])
                if full_name not in avions:
                    avion = create_avion(full_name, lgn, configs['#ALL'].have_teams)
                    avions[full_name] = avion
                else:
                    avions = add_values(avions, full_name, lgn)
                y += 1
    tournoi = Tournoi(avions, rounds)
    tournoi.date = date
    tournoi.duree = duree
    csv_global.append(table_maker(p, f'tournoi.csv', tournoi.tri_avions(False, configs), False, configs, tournoi.date,
                                  tournoi.duree, False, None))
    nbr_heats = 0
    for rd in tournoi.lst_rounds:
        nbr_heats += len(rd.heats)
    tournement = p.name
    if tournement == '':
        tournement = Path.cwd().parts[-1]
    l_csv_g = len(csv_global)
    with open(p / f'global {tournement}.csv', mode='w') as table_global:
        table_writer = csv.writer(table_global, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL, dialect='unix')
        for x in range(l_csv_g):
            table = csv_global[x]
            y = 0
            for lgn in table:
                lgn = info_lat_glob(x, y, lgn, l_csv_g, tournement, nbr_heats, len(tournoi.lst_rounds))
                table_writer.writerow(lgn)
                y += 1
            table_writer.writerow([])
    if configs['#ALL'].have_teams:
        team_f(p, avions, configs, date, duree)


def config_file_func(p):
    for f in p.iterdir():
        if str(f) == 'pacctak_config.txt':
            lignes = []
            with open(f) as config_file:
                for lgn in config_file:
                    lignes.append(lgn.strip('\n'))
            if len(lignes) != 12:
                config = Config(1, 2, 0.5, 1, 0.0002, 0.00002, 0, 2, 0, 0, True)
                return {'#ALL': config}
            m = re.match(r'score_position:(?P<score_position>.+)$', lignes[1])
            score_position = float(m['score_position'])
            m = re.match(r'score_nbr_clean_k_b:(?P<score_nbr_clean_k_b>.+)$', lignes[2])
            score_nbr_clean_k_b = float(m['score_nbr_clean_k_b'])
            m = re.match(r'score_nbr_clean_k_m:(?P<score_nbr_clean_k_m>.+)$', lignes[3])
            score_nbr_clean_k_m = float(m['score_nbr_clean_k_m'])
            m = re.match(r'score_nbr_clean_k_r:(?P<score_nbr_clean_k_r>.+)$', lignes[4])
            score_nbr_clean_k_r = float(m['score_nbr_clean_k_r'])
            m = re.match(r'score_bullet_damages:(?P<score_bullet_damages>.+)$', lignes[5])
            score_bullet_damages = float(m['score_bullet_damages'])
            m = re.match(r'score_missiles_damages:(?P<score_missiles_damages>.+)$', lignes[6])
            score_missiles_damages = float(m['score_missiles_damages'])
            m = re.match(r'score_accuracy:(?P<score_accuracy>.+)$', lignes[7])
            score_accuracy = float(m['score_accuracy'])
            m = re.match(r'score_ramming:(?P<score_ramming>.+)$', lignes[8])
            score_ramming = float(m['score_ramming'])
            m = re.match(r'parts_destructed_by_ram:(?P<parts_destructed_by_ram>.+)$', lignes[9])
            parts_destructed_by_ram = float(m['parts_destructed_by_ram'])
            m = re.match(r'score_dead_time:(?P<score_dead_time>.+)$', lignes[10])
            score_dead_time = float(m['score_dead_time'])
            m = re.match(r'heats_round:(?P<heats_round>.+)$', lignes[11])
            heats_round = bool(m['heats_round'])
            config = Config(score_position, score_nbr_clean_k_b, score_nbr_clean_k_m, score_nbr_clean_k_r,
                            score_bullet_damages, score_missiles_damages, score_accuracy, score_ramming,
                            parts_destructed_by_ram, score_dead_time, heats_round)
            return {'#ALL': config}
    config = Config(1, 2, 0.5, 1, 0.0002, 0.00002, 0, 2, 0, 0, True)
    config.path = p
    return {'#ALL': config}


def set_list(text, nbr_tournaments):
    separated_text = text.split('-')
    numbers = []
    for carac in separated_text:
        n = carac.strip()
        m = re.match(r'(?P<n>\d+)$', n)
        if m is None:
            return None
        if 0 > int(m['n']) > nbr_tournaments:
            return None
        numbers.append(int(m['n']))
    return numbers


def creat_multi_tournament(p, list_tournaments):
    total_name = 'Total Tournament '
    for t in list_tournaments:
        m = re.match(r'Tournament (?P<nbrs>\d+)', t.name)
        total_name += m['nbrs'] + ' '
    total_name = total_name[0:-1]
    fic_here = []
    for n in p.iterdir():
        fic_here.append(n)
    p_tt = p / total_name
    if p_tt not in fic_here:
        Path.mkdir(p_tt)
    nbr_r = 0
    rounds = []
    for t in list_tournaments:
        for round_n in t.iterdir():
            m = re.match(r'Round (?P<nbrs>\d+)', round_n.name)
            if m is None:
                continue
            for heat_n in round_n.iterdir():
                m = re.match(r'(?P<nbrs>\d+)-Heat (?P<nbr>\d+)', heat_n.name)
                if m is None:
                    continue
                with heat_n.open('r') as file:
                    heat_log = file.read().split('\n')
                    while len(rounds) - 1 < nbr_r:
                        rounds.append([])
                    rounds[nbr_r].append((heat_n.name, heat_log))
            nbr_r += 1
    fic_here = []
    for n in p_tt.iterdir():
        fic_here.append(n)
    for i in range(nbr_r):
        p_r = p_tt / f'Round {i}'
        if p_r not in fic_here:
            Path.mkdir(p_r)
        for name, text in rounds[i]:
            with open(p_r / name, mode='w') as txt:
                for line in text:
                    txt.write(line + '\n')
    return p_tt


def search_tournament(p):
    tournois = []
    for f in p.iterdir():
        if str(f.parts[-1])[0:11] == 'Tournament ' and len(str(f.parts[-1])) == 19:
            tournois.append(f)
    aff = 'Choisis un tournoi parmis ceux ci :\n'
    for i, t in enumerate(tournois):
        aff += f'[{i}] : {str(t.parts[-1])}\n'
    aff += '\n[numero] : '
    answere = None
    while answere is None:
        answere = set_list(input(aff), len(tournois) - 1)
        if answere is None:
            print(f'Il faut un ou plusieurs nombres (separes par des tirets) entre [0;{len(tournois) - 1}]')
    tournois_selectionnes = []
    for i in answere:
        tournois_selectionnes.append(tournois[i])
    if len(tournois_selectionnes) == 1:
        return tournois_selectionnes[0]
    return creat_multi_tournament(p, tournois_selectionnes)


def main():
    p = Path.cwd()
    if p.parts[-1] == 'Logs':
        path_tournament = search_tournament(p)
    else:
        path_tournament = p
    path_tournament = path_tournament.relative_to(Path.cwd())
    print('pt :', path_tournament)
    configs = config_file_func(path_tournament)
    for k, v in configs.items():
        print(k)
        print(str(v))
    configs, re_an_logs = menu(path_tournament, configs)
    if re_an_logs:
        heat_f(path_tournament, configs)
    rounds, csv_global = round_f(path_tournament, configs)
    tournament_f(path_tournament, csv_global, rounds, configs)
    input('\n\nTout semble avoir bien fonctionné.\n[entrer] pour quitter : ')


if __name__ == '__main__':
    main()
