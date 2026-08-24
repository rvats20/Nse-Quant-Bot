import pandas as pd
from black_scholes import gamma
from config import SPOT_PRICE,RISK_FREE_RATE,TIME_TO_EXPIRY

def compute_gex(df):

    exposures=[]

    for _,row in df.iterrows():

        sigma=row["iv"]/100

        g=gamma(
            SPOT_PRICE,
            row["strike"],
            TIME_TO_EXPIRY,
            RISK_FREE_RATE,
            sigma
        )

        # Dealer positioning convention: dealers are short calls /
        # long puts, so put gamma enters GEX with negative sign.
        sign=-1 if row["type"]=="put" else 1

        exposure=sign*g*row["oi"]*100

        exposures.append({
            "strike":row["strike"],
            "gex":exposure
        })

    gex_df=pd.DataFrame(exposures)

    levels=gex_df.groupby("strike").sum().reset_index()

    return levels

def find_gamma_walls(levels):

    top=levels.sort_values("gex",ascending=False).head(5)

    return top
