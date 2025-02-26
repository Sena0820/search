# coding=utf-8
from simpleai.search.utils import BoundedPriorityQueue, InverseTransformSampler
from simpleai.search.models import SearchNodeValueOrdered
import math
import random


def _all_expander(fringe, iteration, viewer):
    '''
    Expander that expands all nodes on the fringe.
    '''
    expanded_neighbors = [node.expand(local_search=True)
                          for node in fringe]

    if viewer:
        viewer.event('expanded', list(fringe), expanded_neighbors)

    list(map(fringe.extend, expanded_neighbors))


def beam(problem, beam_size=100, iterations_limit=0, viewer=None):
    '''
    Beam search.

    beam_size is the size of the beam.
    If iterations_limit is specified, the algorithm will end after that
    number of iterations. Else, it will continue until it can't find a
    better node than the current one.
    Requires: SearchProblem.actions, SearchProblem.result, SearchProblem.value,
    and SearchProblem.generate_random_state.
    '''
    return _local_search(problem,
                         _all_expander,
                         iterations_limit=iterations_limit,
                         fringe_size=beam_size,
                         random_initial_states=True,
                         stop_when_no_better=iterations_limit == 0,
                         viewer=viewer)


def _first_expander(fringe, iteration, viewer):
    '''
    Expander that expands only the first node on the fringe.
    '''
    current = fringe[0]
    neighbors = current.expand(local_search=True)

    if viewer:
        viewer.event('expanded', [current], [neighbors])

    fringe.extend(neighbors)


def beam_best_first(problem, beam_size=100, iterations_limit=0, viewer=None):
    '''
    Beam search best first.

    beam_size is the size of the beam.
    If iterations_limit is specified, the algorithm will end after that
    number of iterations. Else, it will continue until it can't find a
    better node than the current one.
    Requires: SearchProblem.actions, SearchProblem.result, and
    SearchProblem.value.
    '''
    return _local_search(problem,
                         _first_expander,
                         iterations_limit=iterations_limit,
                         fringe_size=beam_size,
                         random_initial_states=True,
                         stop_when_no_better=iterations_limit == 0,
                         viewer=viewer)


def hill_climbing(problem, iterations_limit=0, viewer=None):
    '''
    Hill climbing search.

    If iterations_limit is specified, the algorithm will end after that
    number of iterations. Else, it will continue until it can't find a
    better node than the current one.
    Requires: SearchProblem.actions, SearchProblem.result, and
    SearchProblem.value.
    '''
    return _local_search(problem,
                         _first_expander,
                         iterations_limit=iterations_limit,
                         fringe_size=1,
                         stop_when_no_better=True,
                         viewer=viewer)


def _random_best_expander(fringe, iteration, viewer):
    '''
    Expander that expands one randomly chosen nodes on the fringe that
    is better than the current (first) node.
    '''
    current = fringe[0]
    neighbors = current.expand(local_search=True)
    if viewer:
        viewer.event('expanded', [current], [neighbors])

    betters = [n for n in neighbors
               if n.value > current.value]
    if betters:
        chosen = random.choice(betters)
        if viewer:
            viewer.event('chosen_node', chosen)
        fringe.append(chosen)


def hill_climbing_stochastic(problem, iterations_limit=0, viewer=None):
    '''
    Stochastic hill climbing.

    If iterations_limit is specified, the algorithm will end after that
    number of iterations. Else, it will continue until it can't find a
    better node than the current one.
    Requires: SearchProblem.actions, SearchProblem.result, and
    SearchProblem.value.
    '''
    return _local_search(problem,
                         _random_best_expander,
                         iterations_limit=iterations_limit,
                         fringe_size=1,
                         stop_when_no_better=iterations_limit == 0,
                         viewer=viewer)


def hill_climbing_random_restarts(problem, restarts_limit, iterations_limit=0, viewer=None):
    '''
    Hill climbing with random restarts.

    restarts_limit specifies the number of times hill_climbing will be runned.
    If iterations_limit is specified, each hill_climbing will end after that
    number of iterations. Else, it will continue until it can't find a
    better node than the current one.
    Requires: SearchProblem.actions, SearchProblem.result, SearchProblem.value,
    and SearchProblem.generate_random_state.
    '''
    restarts = 0
    best = None

    while restarts < restarts_limit:
        new = _local_search(problem,
                            _first_expander,
                            iterations_limit=iterations_limit,
                            fringe_size=1,
                            random_initial_states=True,
                            stop_when_no_better=True,
                            viewer=viewer)

        if not best or best.value < new.value:
            best = new

        restarts += 1

    if viewer:
        viewer.event('no_more_runs', best, 'returned after %i runs' % restarts_limit)

    return best


# Math literally copied from aima-python
def _exp_schedule(iteration, k=20, lam=0.005, limit=100):
    '''
    Possible scheduler for simulated_annealing, based on the aima example.
    '''
    return k * math.exp(-lam * iteration)


def _create_simulated_annealing_expander(schedule):
    '''
    Creates an expander that has a random chance to choose a node that is worse
    than the current (first) node, but that chance decreases with time.
    '''

    def _expander(fringe, iteration, viewer):
        T = schedule(iteration)
        current = fringe[0]
        neighbors = current.expand(local_search=True)

        if viewer:
            viewer.event('expanded', [current], [neighbors])

        if neighbors:
            succ = random.choice(neighbors)
            delta_e = succ.value - current.value
            if delta_e > 0 or random.random() < math.exp(delta_e / T):
                fringe.pop()
                fringe.append(succ)

                if viewer:
                    viewer.event('chosen_node', succ)

    return _expander


def simulated_annealing(problem, schedule=_exp_schedule, iterations_limit=0, viewer=None):
    '''
    Simulated annealing.

    schedule is the scheduling function that decides the chance to choose worst
    nodes depending on the time.
    If iterations_limit is specified, the algorithm will end after that
    number of iterations. Else, it will continue until it can't find a
    better node than the current one.
    Requires: SearchProblem.actions, SearchProblem.result, and
    SearchProblem.value.
    '''
    return _local_search(problem,
                         _create_simulated_annealing_expander(schedule),
                         iterations_limit=iterations_limit,
                         fringe_size=1,
                         stop_when_no_better=iterations_limit == 0,
                         viewer=viewer)


def _create_genetic_expander(problem, crossover_rate, mutation_chance):
    '''
    Creates an expander that expands the bests nodes of the population,
    crossing over them.
    '''
    '''global elite_list
    elite_list = []'''

    def _expander(fringe, iteration, viewer):  # 毎世代ごとに呼ばれる
        fitness = [x.value for x in fringe]  # 遺伝子であるベクトルの配列、weightでもある
        sampler = InverseTransformSampler(fitness, fringe)  # おそらく個体、objectでもある
        new_generation = []  # 新世代
        # これらのリストはこの関数呼び出す毎に初期化されている

        elitest_node = sampler.best()
        new_generation.append(elitest_node)

        expanded_nodes = []
        expanded_neighbors = []
        '''elite = fringe[0]# ここでのエラーではない
        elite_list.append(elite)'''

        # for _ in fringe:# 個体1個につき毎回行う、一個体にフォーカスしていることを頭に入れる
        #     node1 = sampler.sample() # 良く分からない、おそらく親世代から親とする個体を二つ選んでいる
        #     node2 = sampler.sample()
        #     # if random.random() < 0.2:
        #     #     child = problem.crossover(node1.state, node2.state)  # 二つから新しい個体を生み出している
        #     #     # このcrossoverは自分で設定したやつ。改善の余地あるかも
        #     # else:
        #     action = 'crossover'
        #     # この上の一点交叉の箇所らへんでエリート戦略について書けそう
        #     if random.random() < mutation_chance:
        #         child = problem.mutate(child)
        #         action += '+mutation'

        for _ in range(len(fringe) - 1):
            action = ''
            did_crossover = False
            if random.random() < crossover_rate:
                node1 = sampler.sample()
                node2 = sampler.sample()
                child = problem.crossover(node1.state, node2.state)
                action = 'crossover'
                did_crossover = True
            else:
                selected = sampler.sample() # 親世代からほぼランダムで一個選択している。だから親世代と同じやつが選ばれるはず
                child = selected.state

            if random.random() < mutation_chance:
                # Noooouuu! she is... he is... *IT* is a mutant!
                child = problem.mutate(child)
                action = action + '+mutation' if 0 < len(action) else 'mutation'

            child_node = SearchNodeValueOrdered(state=child, problem=problem,
                                                action=action)  # これが意味わからない、聞く、nodeの順番逆にしてる？意味わからない
            # valueを自分の設定したvalueに置き換えている、stateがchildなこと忘れず
            # child_nodeに何が入っているのか？おそらく一個体の遺伝子情報だと考えられる
            new_generation.append(child_node)  # 新世代のリストに個体を一個追加している

            if did_crossover:
                expanded_nodes.append(node1)
                expanded_neighbors.append([child_node])
                expanded_nodes.append(node2)
                expanded_neighbors.append([child_node])
            else:
                expanded_nodes.append(selected)
                expanded_neighbors.append([child_node])
            # expanded_nodes.append(node1)# これらは途中経過のために作っているだけか？
            # expanded_neighbors.append([child_node])
            # # このneighborが何のためにあるか調べる
            # expanded_nodes.append(node2)
            # expanded_neighbors.append([child_node])#何で2回？これは分からないが何か意味ありそう

        if viewer:
            viewer.event('expanded', expanded_nodes, expanded_neighbors)

        fringe.clear()  # 毎回fringeをリセットしている。親世代の削除とも言える
        '''new_generation[0] = elite[0]　# これに対するエラー'''
        for node in new_generation:
            fringe.append(node)
            # ここで新しく子世代を親世代に変更？
            # ここにエリートをfringeに入れるようにしてあげられたらオッケー?,いや、crossoverなどする前に親世代の中で一番いいやつ残さないといけない

    return _expander


def genetic(problem, population_size=100, crossover_rate=0.6, mutation_chance=0.1,
            iterations_limit=0, viewer=None):
    '''
    Genetic search.

    population_size specifies the size of the population (ORLY).
    mutation_chance specifies the probability of a mutation on a child,
    varying from 0 to 1.
    If iterations_limit is specified, the algorithm will end after that
    number of iterations. Else, it will continue until it can't find a
    better node than the current one.
    Requires: SearchProblem.generate_random_state, SearchProblem.crossover,
    SearchProblem.mutate and SearchProblem.value.
    '''
    return _local_search(problem,
                         _create_genetic_expander(problem, crossover_rate, mutation_chance),
                         iterations_limit=iterations_limit,
                         fringe_size=population_size,
                         random_initial_states=True,
                         stop_when_no_better=iterations_limit == 0,
                         viewer=viewer)


def _local_search(problem, fringe_expander, iterations_limit=0, fringe_size=1,
                  random_initial_states=False, stop_when_no_better=True,
                  viewer=None):
    '''
    Basic algorithm for all local search algorithms.
    '''
    if viewer:
        viewer.event('started')

    fringe = BoundedPriorityQueue(fringe_size)
    if random_initial_states:
        for _ in range(fringe_size):
            s = problem.generate_random_state()
            fringe.append(SearchNodeValueOrdered(state=s, problem=problem))
    else:
        fringe.append(SearchNodeValueOrdered(state=problem.initial_state,
                                             problem=problem))

    finish_reason = ''
    iteration = 0
    run = True
    best = None
    word_list = []
    while run:
        # if viewer:
        #     viewer.event('new_iteration', list(fringe))

        old_best = fringe[0]
        # print(f"old:{fringe[0]}")
        fringe_expander(fringe, iteration, viewer)
        # newnodeの入ったexpanded_neighborsがfringeに入れられた状態
        best = fringe[0]
        word_list.append(fringe[0])
        # print(f"new:{fringe[0]}")
        # print(f"fringe:{fringe[1]}")

        iteration += 1
        print(f"↑{iteration}回目")
        print("                        ")
        if iterations_limit and iteration >= iterations_limit:
            run = False
            finish_reason = 'reaching iteration limit'
        elif old_best.value >= best.value and stop_when_no_better:
            run = False
            finish_reason = 'not being able to improve solution'
    double_list = []
    for i in word_list:
        if i not in double_list:
            double_list.append(i)
    print(f"探索に掛かった単語数：{len(double_list)}")
    print(f"探索過程：{double_list}")
    if viewer:
        viewer.event('finished', fringe, best, 'returned after %s' % finish_reason)

    return best
