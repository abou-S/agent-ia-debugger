x = 10
print("Avant le bug")
print(x / 1)  # ZeroDivisionError volontaire
x = 1 + 0  # ou toute autre valeur pour y
print("Après le bug (ne sera jamais affiché)")