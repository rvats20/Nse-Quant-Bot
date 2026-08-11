from data_fetcher import fetch_option_chain
from lottery_calls import find_lottery_calls
from iron_condor import build_condor
from gex_engine import compute_gex,find_gamma_walls
from config import SPOT_PRICE

def main():

    df=fetch_option_chain()

    print("Building strategies...")

    condor=build_condor(df,SPOT_PRICE)
    print("Iron Condor:",condor)

    lottery=find_lottery_calls(df,SPOT_PRICE)
    print("High Risk Calls:",lottery[:5])

    gex=compute_gex(df)

    walls=find_gamma_walls(gex)

    print("Gamma Wall Levels")
    print(walls)

if __name__=="__main__":
    main()
