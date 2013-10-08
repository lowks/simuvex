#!/usr/bin/env python
'''This module handles constraint generation.'''

import os
import z3

# importing stuff into the module namespace
from s_value import ConcretizingException
from s_irsb import SymbolicIRSB
from s_irstmt import SymbolicIRStmt
from s_exit import SymbolicExit
from s_state import SymbolicState

# to make the stupid thing stop complaining
SymbolicIRStmt, ConcretizingException

import logging
l = logging.getLogger("pysex")

try:
	z3_path = os.environ["Z3PATH"]
except Exception:
	z3_path = "/opt/python/lib/"
z3.init(z3_path + "libz3.so")

def translate_bytes(base, bytes, entry, initial_state = None, bits=64):
	l.debug("Translating %d bytes, starting from %x" % (len(bytes), entry))
	remaining_exits = [ ]
	visited_starts = set()
	blocks = [ ]
	unsat_exits = [ ]
	exits_out = [ ]

	# take an initial exit
	entry_point = SymbolicExit(empty = True)
	entry_point.state = initial_state.copy_after() if initial_state else SymbolicState()
	entry_point.s_target = z3.BitVecVal(entry, bits)
	entry_point.s_jumpkind = "Ijk_Boring"
	remaining_exits.append(entry_point)

	# and go!
	while remaining_exits:
		current_exit = remaining_exits[0]
		remaining_exits = remaining_exits[1:]

		# get the concrete value
		# TODO: deal with possibility of multiple exits
		l.debug("Concretizing start value...")
		if not current_exit.reachable():
			l.warning("UNSAT exit condition")
			unsat_exits.append(current_exit)
			continue

		try:
			concrete_start = current_exit.concretize()
		except ConcretizingException:
			l.warning("Exit has many possible values.")

		l.debug("... concretized start: %x" % concrete_start)
		byte_start = concrete_start - base
		if byte_start < 0 or byte_start >= len(bytes):
			l.info("Exit jumps to %x, outside of the provided bytes." % concrete_start)
			exits_out.append(current_exit)
			continue

		if concrete_start not in visited_starts:
			l.debug("... processing block")
			visited_starts.add(concrete_start)
			sirsb = SymbolicIRSB(base=base, bytes=bytes, byte_start=byte_start, initial_state=current_exit.state)
			exits = sirsb.exits()
			remaining_exits.extend(exits)
			l.debug("Got %d exits" % len(exits))

			blocks.append((concrete_start, sirsb))

	return blocks, exits_out, unsat_exits