import collections
import re

stats = collections.defaultdict(lambda: {'win': 0, 'loss': 0})

with open('pattern_events.txt', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        
        # 0, 1, 1  |  2026-04-11 09:01:27  |  bad%=40.0%  |  list=1  |  CLICKED=NO  |  [<=40% ZONE]
        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 4: continue
        
        pattern = parts[0]
        bad_pct = parts[2]
        lst = parts[3]
        
        is_win = (pattern == '0, 1, 1')
        is_loss = (pattern == '0, 1, 0')
        
        if not (is_win or is_loss): continue
        
        # We can analyze by bad% alone, list alone, and bad%+list
        key_all = 'ALL'
        key_bad = bad_pct
        key_list = lst
        key_both = f'{bad_pct} + {lst}'
        
        keys = [key_all, key_bad, key_list, key_both]
        for k in keys:
            if is_win: stats[k]['win'] += 1
            if is_loss: stats[k]['loss'] += 1

print('--- Win/Loss Analysis of pattern_events.txt ---')
print(f'Target: <=1 loss for every 5 wins (Win Rate >= 83.3%)')
print(f'{"Condition":<25} | {"Wins":<5} | {"Losses":<6} | {"Win Rate":<8} | {"Ratio (W:L)"}')
print('-' * 70)

sorted_stats = sorted(stats.items(), key=lambda x: -x[1]['win'])
for k, v in sorted_stats:
    w = v['win']
    l = v['loss']
    total = w + l
    if total < 2: continue  # require minimum sample size
    
    rate = (w / total) * 100
    ratio = f'{w}:{l}'
    
    # Highlight conditions that meet the user requirement
    marker = '[MATCH]' if l == 0 or (w/l) >= 5 else '       '
    print(f'{marker} {k:<23} | {w:<5} | {l:<6} | {rate:>5.1f}%   | {ratio}')
