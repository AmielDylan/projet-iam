import requetes as req

# med = "ABSTRAL"

# listClasses_1 = []
# if eval(req.isSpecialite(med)):
#     print(med + " is Spé")
#     listSubstancesId = req.getSubstanceIdFromSpe(med)
#     for value in listSubstancesId:
#         res = req.getClassesIdFromSubstance(req.getSubstanceName(value))
#         for cs_value in res:
#             listClasses_1.append(cs_value)
            
#         if eval(req.isClasse(req.getSubstanceName(value))):
#             print(req.getSubstanceName(value) + " in " + med + " is also Classe")
#             listClasses_1.append(req.getClasseId(req.getSubstanceName(value)))

# if eval(req.isClasse(med)):
#     print(med + " is Classe")
#     listClasses_1.append(req.getClasseId(med))

# if eval(req.isSubstance(med)):
#     print(med + " is SUb")
#     for value in req.getClassesIdFromSubstance(med):
#       listClasses_1.append(value)

# print(listClasses_1)

print(req.getInteractionsMed("novaten ","amiodarone sandoz"))

