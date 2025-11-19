x = 10
print("Avant le bug")
print(x)  # Remplacement pour éviter la division par zéro
a = 0  # Déclaration de la variable 'a' pour éviter une erreur NameError
print(a)
x = 1  # Remplacement pour éviter une erreur NameError due à 'y'
print("Après le bug (ne sera jamais affiché)")