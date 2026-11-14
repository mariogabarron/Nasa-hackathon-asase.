import getter

df = getter.get_tabla("2025-10-01", "2026-03-31", (9.5850, -0.8420), None)

df.to_csv("output.csv")

print(df.keys())