# Can't import * in this module because of a circular import problem specific to teams
# The TeamCore module can instantiate from a client, but the client needs to use the
# team backend module to request the object for team. To circumvent this there's a
# get_raw method in this module that returns the raw team object, which is then passed
# to the TeamCore module, but if we import * here it introduces the
# circular import problem.
