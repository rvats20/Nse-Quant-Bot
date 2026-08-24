import numpy as np
from scipy.stats import norm

def gamma(S,K,T,r,sigma):

    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return 0.0

    d1=(np.log(S/K)+(r+0.5*sigma**2)*T)/(sigma*np.sqrt(T))

    return norm.pdf(d1)/(S*sigma*np.sqrt(T))

def black_scholes(S,K,T,r,sigma,opt="call"):

    d1=(np.log(S/K)+(r+0.5*sigma**2)*T)/(sigma*np.sqrt(T))
    d2=d1-sigma*np.sqrt(T)

    if opt=="call":
        return S*norm.cdf(d1)-K*np.exp(-r*T)*norm.cdf(d2)
    else:
        return K*np.exp(-r*T)*norm.cdf(-d2)-S*norm.cdf(-d1)
