import numpy as np
import matplotlib.pyplot as plt

t = 1
q = 1
s = 1
b = 4
a = 2
c = 0.03
k = 500
M = 0.5

x_values = []
y_values = []

fig, ax = plt.subplots(figsize=(10, 6))

def calculateBondingCurveValue(counter, s, t):
    s = int(s)
    t = int(t)

    y = 1 + ((M - 1) / (1 + np.exp(-a / k * ((t ** q * b ** (s - 1) * counter) - k)))) + M * (np.exp(-c / k * (t ** q * b ** (s - 1) * counter)) - 1) - ((M - 1) / (1 + np.exp(a)))

    return y

def test():
    counter = 0
    while counter <= 100000:
        y = 1 + ((M - 1) / (1 + np.exp(-a / k * ((t ** q * b ** (s - 1) * counter) - k)))) + M * (np.exp(-c / k * (t ** q * b ** (s - 1) * counter)) - 1) - ((M - 1) / (1 + np.exp(a)))

        x_values.append(counter)
        y_values.append(y)
        # print(f"Step {counter}: X = {counter}")

        counter += 1

    ax.plot(x_values, y_values, color='red')

    ax.set_title("Bonding curve test")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")

    ax.set_ylim([0, 1.5])
    ax.set_yticks(np.arange(0, 1.6, 0.1))

    # Display the plot
    plt.show()

#test()