from __future__ import print_function
from __future__ import division
from pyomo.opt import SolverFactory
from pyomo.environ import *
from ..problem_classes.heat_exchange import *
from solver_statistics import Solver_Statistics
from ..io_modules.readers import read_nodes_explored

def solve_transshipment_mip(test_set,test_id,solver,timeout,inst):

	model = AbstractModel()
	
	model.n = Param(within=NonNegativeIntegers, initialize=inst.n) # number of hot streams
	model.m = Param(within=NonNegativeIntegers, initialize=inst.m) # number of cold streams
	model.k = Param(within=NonNegativeIntegers, initialize=inst.k) # number of temperature intervals
	
	model.H = RangeSet(0, model.n-1) # set of hot streams
	model.C = RangeSet(0, model.m-1) # set of cold streams
	model.TI = RangeSet(0, model.k-1) # set of temperature intervals
	model.Rset = RangeSet(0, model.k) # set of residuals 

	# Parameter: heat of hot stream i in temperature interval t 
	model.QH = Param(model.H, model.TI, within=NonNegativeReals, initialize=lambda model, i, t: inst.QH[i][t])

	# Paramter: heat of cold stream j in temperature interval t
	model.QC = Param(model.C, model.TI, within=NonNegativeReals, initialize=lambda model, j, t: inst.QC[j][t])

	# Parameter: residual heat entering temperature interval t
	#model.R = Param(model.Rset, within=NonNegativeReals, initialize=lambda model, t: inst.R[t])
	
	# Parameter: upper bound on the total heat exchanged between hot stream i and cold stream j
	model.U = Param(model.H, model.C, within=NonNegativeReals, initialize=lambda model, i, j: inst.U[i][j])
	
	# Variable: number of matches
	model.matches = Var(within=NonNegativeIntegers)
    
	# Variable: binary specifying whether hot stream i is matched to cold stream j
	model.y = Var(model.H, model.C, within=Binary)
    
	# Variable: heat transferred to cold stream j within temperature interval t from hot stream i
	model.q = Var(model.H, model.C, model.TI, within=NonNegativeReals)
	
	# Variable: residual heat of hot stream i entering temperature interval t
	model.r = Var(model.H,  model.Rset, within=NonNegativeReals)
    
	# Objective: minimization of the number of matches
	def number_matches_rule(model):
		return model.matches
	model.obj_value = Objective(rule=number_matches_rule, sense=minimize)
	
	# Constraint: matches enumeration
	def matches_sum_rule(model):
		return model.matches == sum(model.y[i,j] for i in model.H for j in model.C)
	model.matches_sum_constraint = Constraint(rule=matches_sum_rule)   
    
	#Constraint: heat conservation of hot streams
	def hot_conservation_rule(model, i, t):
		return sum(model.q[i,j,t] for j in model.C) + model.r[i,t+1] == model.QH[i,t] + model.r[i,t]
	model.hot_conservation_constraint = Constraint(model.H, model.TI, rule=hot_conservation_rule)
    
	#Constraint: heat conservation of cold streams
	def cold_conservation_rule(model, j, t):
		return sum(model.q[i,j,t] for i in model.H) == model.QC[j,t]
	model.cold_conservation_constraint = Constraint(model.C, model.TI, rule=cold_conservation_rule)
    
	# Constraint: matched streams
	def matched_streams_rule(model, i, j):
		return sum(model.q[i,j,t] for t in model.TI) <= model.U[i,j]*model.y[i,j]
	model.matched_streams_constraint = Constraint(model.H, model.C, rule=matched_streams_rule)    

	##Constraint: residual conservation
	#def residual_conservation_rule(model, t):
		#return sum(model.r[i,t] for i in model.H) == model.R[t]
	#model.residual_conservation_constraint = Constraint(model.Rset, rule=residual_conservation_rule)  
	
	#Constraint: zero residuals
	def residual_conservation_rule(model):
		return sum(model.r[i,0] for i in model.H) == 0
	model.residual_conservation_constraint = Constraint(rule=residual_conservation_rule)  

	#Constraint: zero residuals
	def residual_conservation_rule1(model):
		return sum(model.r[i,inst.k] for i in model.H) == 0
	model.residual_conservation_constraint1 = Constraint(rule=residual_conservation_rule1) 

	opt = SolverFactory(solver)
	opt.options['threads'] = 1
	opt.options['logfile'] = 'data/mip_solutions/'+test_set+'/transshipment/'+test_id+'_'+solver+'.log'
	opt.options['mipgap'] = 0.04
	opt.options['timelimit'] = timeout
	mip_instance = model.create_instance()
	results = opt.solve(mip_instance)
	
	elapsed_time = results.solver.time
	nodes_explored = read_nodes_explored(test_set,test_id,solver,'transshipment')
	lower_bound = results.problem.lower_bound
	upper_bound = results.problem.upper_bound
	
	stats = Solver_Statistics(elapsed_time, nodes_explored, lower_bound, upper_bound)
	
	matches=mip_instance.matches.value
	y=[[mip_instance.y[i,j].value for j in range(inst.m)] for i in range(inst.n)]
	q=[[[mip_instance.q[i,j,t].value for t in range(inst.k)] for j in range(inst.m)] for i in range(inst.n)]
	r=[[mip_instance.r[i,t].value for t in range(inst.k)] for i in range(inst.n)]
	
	sol=Heat_Exchange('transshipment',inst.n,inst.m,inst.k,matches,y,q,r)
	return (sol, stats)
	
