#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 17 02:16:25 2025

@author: billyeskel
"""

import pandas as pd
import matplotlib.pyplot as plt

# Load data
df = pd.read_excel("/Users/billyeskel/var/outputs/pwbi_dyn/demo_shift/official/Proximity Data.xlsx")
df['Date'] = pd.to_datetime(df['Date'])

# Pick your desired BarraIds
barra_ids = ["USA2HB1", "USAA681"]

# -----------------------------------------------------------------------------
# Smart scaling function (positive/negative split with padding)
# -----------------------------------------------------------------------------
def smart_scale(series):
    smin = series.min()
    smax = series.max()

    # Entirely negative
    if smax <= 0:
        ymin = smin * 1.10     # expand downward
        ymax = smax * 0.90     # lift slightly toward 0
        return ymin, ymax

    # Entirely positive
    if smin >= 0:
        ymin = smin * 0.90     # pull slightly toward 0
        ymax = smax * 1.10     # expand upward
        return ymin, ymax

    # Crosses zero → use symmetrical range
    return -1, 1

# -----------------------------------------------------------------------------
# Plot each BarraId
# -----------------------------------------------------------------------------
for bid in barra_ids:
    sub = df[df["BarraId"] == bid]
    pivot = sub.pivot(index="Date", columns="ContextualVarGroup", values="value")
    
    vars_order = ["DIVYILD", "SIZE", "SpeRisk"]
    vars_present = [v for v in vars_order if v in pivot.columns]

    fig, axes = plt.subplots(len(vars_present), 1, figsize=(10, 8), sharex=True)
    if len(vars_present) == 1:
        axes = [axes]

    fig.suptitle(f"Trellis Time Series for {bid}")

    for ax, var in zip(axes, vars_present):

        series = pivot[var].dropna()

        # Get smart scale
        ymin, ymax = smart_scale(series)

        # Guarantee ymin < ymax
        ymin, ymax = min(ymin, ymax), max(ymin, ymax)

        ax.set_ylim(ymin, ymax)

        ax.plot(series.index, series)
        ax.set_title(var)
        ax.set_ylabel("Value")

    axes[-1].set_xlabel("Date")
    plt.tight_layout()
    plt.show()
