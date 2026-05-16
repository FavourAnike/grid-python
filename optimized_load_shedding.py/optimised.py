# =========================
# Load libraries
# =========================
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import os

# =========================
# Reproducibility (VERY IMPORTANT)
# =========================
np.random.seed(42)

# =========================
# Create results folder
# =========================
if not os.path.exists("results"):
    os.makedirs("results")

# =========================
# Load dataset
# =========================
df = pd.read_excel("nigeria_grid_dataset.xlsx")

# =========================
# Simulation setup
# =========================
hours = 24
results = []

# =========================
# Simulation loop
# =========================
for hour in range(hours):

    temp_df = df.copy()

    # =========================
    # Dynamic supply
    # =========================
    if np.random.rand() < 0.2:
        total_supply = np.random.uniform(2500, 3200)
    else:
        total_supply = np.random.uniform(3500, 5000)
    # if np.random.rand() < 0.3:
    #     total_supply = np.random.uniform(2200, 3000)
    # else:
    #     total_supply = np.random.uniform(2800, 3500)

    # =========================
    # Shuffle regions
    # =========================
    temp_df = temp_df.sample(frac=1).reset_index(drop=True)

    # =========================
    # Realistic demand
    # =========================
    temp_df["Demand_MW"] = temp_df["Base_Load_MW"] + \
        (temp_df["Peak_Demand_MW"] - temp_df["Base_Load_MW"]) * \
        np.random.uniform(0.5, 1.0, len(df))

    total_demand = temp_df["Demand_MW"].sum()
    # time_factor = 0.8 + 0.6 * np.sin(hour / 24 * 2* np.pi)
    # temp_df["Demand_MW"]= temp_df["Base_Load_MW"] + \
    #     (temp_df["Peak_Demand_MW"] - temp_df["Base_Load_MW"]) * time_factor * np.random.uniform(0.95, 1.1, len(df))
    
    # total_demand = temp_df["Demand_MW"].sum()
    # if total_demand < total_supply:
    #     total_supply = total_demand * np.random.uniform(0.7, 0.95)

    # print(f"Hour {hour}: Demand={total_demand:.0f}, Supply={total_supply:.0f}")

    # =========================
    # Deficit
    # =========================
    deficit = max(total_demand - total_supply, 0)
    # deficit = max(total_demand - total_supply, 0)
    # if deficit < 200:
    #     deficit *= 1.5

    # =========================
    # Strategy A (Proportional)
    # =========================
    if deficit > 0:
        temp_df["Shed_A"] = (temp_df["Demand_MW"] / total_demand) * deficit
    else:
        temp_df["Shed_A"] = 0.0

    temp_df["Critical_A"] = temp_df["Shed_A"].clip(upper=temp_df["Critical_Load_MW"])

    # =========================
    # Strategy B (BEST - Smart Protection)
    # =========================
    temp_df["Shed_B"] = 0.0
    remaining_deficit = deficit

    # Priority score: higher = more important → protect more
    temp_df["Priority_Score"] = temp_df["Critical_Load_MW"] / temp_df["Demand_MW"]

    # Sort LOW priority first → shed there first
    temp_df = temp_df.sort_values(by="Priority_Score", ascending=True)

    for i in temp_df.index:
        demand = temp_df.loc[i, "Demand_MW"]
        critical = temp_df.loc[i, "Critical_Load_MW"]

        non_critical = max(demand - critical, 0)

        if remaining_deficit > 0:
            shed = min(non_critical, remaining_deficit)
            temp_df.loc[i, "Shed_B"] = shed
            remaining_deficit -= shed

    temp_df = temp_df.sort_index()

    temp_df["Critical_B"] = temp_df["Shed_B"].clip(upper=temp_df["Critical_Load_MW"])

    # =========================
    # Strategy C (WEAKER regional)
    # =========================
    priority = ["South West", "South South"]

    temp_df["Shed_C"] = 0.0
    remaining_deficit = deficit

    # NON-priority first (but limited)
    for i in temp_df[~temp_df["Region"].isin(priority)].index:
        if remaining_deficit > 0:
            demand = temp_df.loc[i, "Demand_MW"]
            non_critical = demand * 0.7   # LIMIT shedding power

            shed = min(non_critical, remaining_deficit)
            temp_df.loc[i, "Shed_C"] = shed
            remaining_deficit -= shed

    # Priority regions (less shedding allowed)
    for i in temp_df[temp_df["Region"].isin(priority)].index:
        if remaining_deficit > 0:
            demand = temp_df.loc[i, "Demand_MW"]
            non_critical = demand * 0.4   # stronger protection

            shed = min(non_critical, remaining_deficit)
            temp_df.loc[i, "Shed_C"] = shed
            remaining_deficit -= shed

    temp_df["Critical_C"] = temp_df["Shed_C"].clip(upper=temp_df["Critical_Load_MW"])

    

    # =========================
    # Store results
    # =========================
    results.append({
        "Hour": hour,
        "Supply": total_supply,
        "Total_Demand": total_demand,
        "Deficit": deficit,
        "Shed_A": temp_df["Shed_A"].sum(),
        "Shed_B": temp_df["Shed_B"].sum(),
        "Shed_C": temp_df["Shed_C"].sum(),
        "Critical_A": temp_df["Critical_A"].sum(),
        "Critical_B": temp_df["Critical_B"].sum(),
        "Critical_C": temp_df["Critical_C"].sum()
    })

# =========================
# Convert to DataFrame
# =========================
results_df = pd.DataFrame(results)
# Fix Hour display for better plotting
results_df["Hour"] = results_df["Hour"].astype(str)

# =========================
# =========================
# Step 5: Performance Metrics
# =========================

# Total Load Shed
totals = results_df[["Shed_A","Shed_B","Shed_C",]].sum()

print("\n=== TOTAL LOAD SHED ===")
print(f"Strategy A: {totals['Shed_A']:.2f} MW")
print(f"Strategy B: {totals['Shed_B']:.2f} MW")
print(f"Strategy C: {totals['Shed_C']:.2f} MW")

# Critical Load Loss
critical = results_df[["Critical_A","Critical_B","Critical_C"]].sum()

print("\n=== CRITICAL LOAD LOSS ===")
print(f"Strategy A: {critical['Critical_A']:.2f} MW")
print(f"Strategy B: {critical['Critical_B']:.2f} MW")
print(f"Strategy C: {critical['Critical_C']:.2f} MW")

# =========================
# Best strategy
# =========================
best_strategy = results_df[["Critical_A","Critical_B","Critical_C"]].sum().idxmin()
print(f"\nBest Strategy: {best_strategy}")

# =========================
# Save results
# =========================
results_df.to_excel("results/optimized_simulation.xlsx", index=False)

# =========================
# Visualizations
# =========================
# # Step 7: Plot Results
# # =========================



# fig1 = px.bar(results_df, x="Hour", y=["Shed_A","Shed_B","Shed_C"],
#        barmode="group", title="Load Shedding by Strategy")


# fig1.show()
# fig1.write_html("results/interactive_load_shedding.html")




# Plotly interactive bar chart
fig = px.bar(results_df, x="Hour", y=["Shed_A","Shed_B","Shed_C"],
             title="Load Shedding Simulation by Strategy",
             labels={"value":"MW", "Hour":"Hour of Day"},
             barmode="group",
             hover_data=["Critical_A","Critical_B","Critical_C"])
fig.show()
fig.write_html("results/interactive_load_shedding.html")
print("\nInteractive dashboard saved as 'results/interactive_load_shedding.html'")



# px.line(results_df, x="Hour", y=["Total_Demand","Supply"],
#         title="Supply vs Demand").show()

fig2 = px.line(results_df, x="Hour", y=["Total_Demand","Supply"],
        title="Supply vs Demand")
fig2.show()
fig2.write_html("results/supply_vs_demand.html")


fig3 = px.line(results_df, x="Hour", y="Deficit",
        title="Power Deficit")
fig3.show()
fig3.write_html("results/deficit_over_time.html")

# =========================
# Heatmap
# =========================
# plt.figure()
# sns.heatmap(results_df[["Shed_A","Shed_B","Shed_C"]].T, annot=True, cmap="YlOrRd")
# plt.title("Load Shedding Heatmap")
# plt.show()



# Seaborn heatmap
shed_df = results_df[["Shed_A","Shed_B","Shed_C"]]
sns.heatmap(shed_df.T, annot=True, cmap="YlOrRd")
plt.title("Load Shedding Heatmap (MW)")
plt.xlabel("Hour")
plt.ylabel("Strategy")
plt.show()