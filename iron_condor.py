from config import IRON_CONDOR_DISTANCE

def build_condor(df,spot):

    calls=df[df["type"]=="call"]
    puts=df[df["type"]=="put"]

    short_call=calls.iloc[(calls["strike"]-spot).abs().argsort()].iloc[0]
    short_put=puts.iloc[(puts["strike"]-spot).abs().argsort()].iloc[0]

    return {
        "short_call":short_call["strike"],
        "long_call":short_call["strike"]+IRON_CONDOR_DISTANCE,
        "short_put":short_put["strike"],
        "long_put":short_put["strike"]-IRON_CONDOR_DISTANCE
    }
