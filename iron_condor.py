from config import IRON_CONDOR_DISTANCE

def build_condor(df,spot):

    calls=df[df["type"]=="call"]
    puts=df[df["type"]=="put"]

    if calls.empty or puts.empty:
        raise ValueError("Option chain must contain both calls and puts")

    short_call=calls.iloc[(calls["strike"]-spot).abs().argsort()].iloc[0]
    short_put=puts.iloc[(puts["strike"]-spot).abs().argsort()].iloc[0]

    def nearest_strike(side_df,target):
        strikes=side_df["strike"].unique()
        return min(strikes,key=lambda s:abs(s-target))

    return {
        "short_call":short_call["strike"],
        "long_call":nearest_strike(calls,short_call["strike"]+IRON_CONDOR_DISTANCE),
        "short_put":short_put["strike"],
        "long_put":nearest_strike(puts,short_put["strike"]-IRON_CONDOR_DISTANCE)
    }
