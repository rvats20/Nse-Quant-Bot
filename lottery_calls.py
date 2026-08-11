from config import LOTTERY_DISTANCE, LOTTERY_PREMIUM_MAX

def find_lottery_calls(df,spot):

    calls=df[df["type"]=="call"]

    results=[]

    for _,row in calls.iterrows():

        if row["strike"]>spot+LOTTERY_DISTANCE and row["price"]<LOTTERY_PREMIUM_MAX:

            results.append({
                "strike":row["strike"],
                "premium":row["price"]
            })

    return results
