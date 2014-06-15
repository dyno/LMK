import operator

def find_extrim(l, wl, wr, _op=operator.ge):
        ti = i = wl
        while i < wr:
            if _op(l[i], l[ti]):
                ti = i
            i += 1

        return ti

def find_pivots(l, look_around=4, _op=operator.ge):
    pivots = []
    # initialize the tentative pivot
    ti = find_extrim(l, 0, look_around + 1, _op)
    time_to_break = False
    while True:
        # verifiy the tentative pivot
        # look back
        wl = max(ti - look_around + 1, 0)
        # look forward
        wr = min(ti + look_around + 1, len(l))
        _ti = find_extrim(l, wl, wr, _op)

        #print "ti, _ti = %d, %d" % (ti, _ti)
        if _ti == ti:
            pivots.append(ti)
            wl = min(ti + look_around + 1, len(l))
        else:
            wl = min(ti + 1, len(l))

        if time_to_break: break

        # find the new tentative pivot
        wr = min(wl + look_around + 1, len(l))
        ti = find_extrim(l, wl , wr, _op)

        if wr == len(l): time_to_break = True


    return pivots

def merged_pivots(history, tops, btms, minimum_distance=5):
    pivots, ti, bi = [], 0, 0
    while ti < len(tops) or bi < len(btms):
        if bi >= len(btms) or (ti < len(tops) and tops[ti] < btms[bi]):
            pivots.append(("H", tops[ti], history[tops[ti]]))
            ti += 1
        elif ti >= len(tops) or (bi < len(btms) and btms[bi] < tops[ti]):
            pivots.append(("L", btms[bi], history[btms[bi]]))
            bi += 1

        _pivots, i = [], 0
        while i < len(pivots):
            target = None
            while i < len(pivots) and pivots[i][0] == "H":
                if not target or target[2] <= pivots[i][2]:
                    target = pivots[i]
                i += 1
            if target: _pivots.append(target)

            target = None
            while i < len(pivots) and pivots[i][0] == "L":
                if not target or target[2] >= pivots[i][2]:
                    target = pivots[i]
                i+= 1
            if target: _pivots.append(target)

    return _pivots


