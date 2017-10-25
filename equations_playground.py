def chance_hit(a, d):
    curve = .2 * abs(a - d)
    perc = float(a) / d
    return int(min(99, max(1, (50 + curve) * perc)))



# chance to hit testing
for a in range(1, 100, 1):
    for d in range(1, 100, 1):
        print('A:{}, D:{}, A->D:{}%, D->A:{}%'.format(a, d, chance_hit(a, d), chance_hit(d, a)))