"""Perguntas da chamada A (proposta SAD v3). Mudar qualquer texto exige subir QUESTIONS_VERSION."""

QUESTIONS_VERSION = "q1"

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]  # mesma ordem dos criteria abaixo

QUESTIONS = {
    "is_defect": {"type": "noul",
                  "instructions": "Does this issue describe a defect (bug) in the software's behavior?"},
    "actionable": {"type": "noul",
                   "instructions": "Could a maintainer act on this issue with what is written, "
                                   "without asking the author for anything else?"},
    "enough_info": {"type": "noul",
                    "instructions": "Does the issue give enough information to reproduce the problem "
                                    "(steps, versions, error output)?"},
    "usage_question": {"type": "noul",
                       "instructions": "Is the author asking how to use the software, rather than "
                                       "reporting a defect or requesting a change?"},
    "severity": {"type": "score",
                 "instructions": "How severe is the problem described in this issue?",
                 "criteria": ["Low: cosmetic issue or minor inconvenience, easy workaround",
                              "Medium: a feature misbehaves for some users, a workaround exists",
                              "High: a major feature is broken or results are wrong, no easy workaround",
                              "Critical: crash, data loss, security vulnerability or outage"]},
}
