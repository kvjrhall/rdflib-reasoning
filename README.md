# Repository Coverage

[Full report](https://htmlpreview.github.io/?https://github.com/kvjrhall/rdflib-reasoning/blob/python-coverage-comment-action-data/htmlcov/index.html)

| Name                                                                      |    Stmts |     Miss |   Cover |   Missing |
|-------------------------------------------------------------------------- | -------: | -------: | ------: | --------: |
| rdflib-reasoning-axioms/src/rdflibr/axiom/\_\_init\_\_.py                 |        0 |        0 |    100% |           |
| rdflib-reasoning-axioms/src/rdflibr/axiom/common.py                       |        6 |        0 |    100% |           |
| rdflib-reasoning-axioms/src/rdflibr/axiom/structural\_element.py          |       77 |       27 |     65% |39, 42, 46, 68, 74, 79, 96, 101-115, 119-140, 149, 154 |
| rdflib-reasoning-engine/src/rdflibr/engine/\_\_init\_\_.py                |        6 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflibr/engine/api.py                         |      158 |        8 |     95% |166, 184, 246-254, 303 |
| rdflib-reasoning-engine/src/rdflibr/engine/batch\_dispatcher.py           |       73 |        2 |     97% |  125, 157 |
| rdflib-reasoning-engine/src/rdflibr/engine/derivation.py                  |       34 |        2 |     94% |   66, 103 |
| rdflib-reasoning-engine/src/rdflibr/engine/proof.py                       |       91 |        1 |     99% |        12 |
| rdflib-reasoning-engine/src/rdflibr/engine/rete/\_\_init\_\_.py           |        8 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflibr/engine/rete/agenda.py                 |       40 |        2 |     95% |    64, 67 |
| rdflib-reasoning-engine/src/rdflibr/engine/rete/callbacks.py              |       16 |        6 |     62% |     41-48 |
| rdflib-reasoning-engine/src/rdflibr/engine/rete/compiler.py               |       79 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflibr/engine/rete/consequents.py            |       37 |        3 |     92% |     76-78 |
| rdflib-reasoning-engine/src/rdflibr/engine/rete/facts.py                  |       15 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflibr/engine/rete/network.py                |      221 |        5 |     98% |302-303, 372, 381, 393 |
| rdflib-reasoning-engine/src/rdflibr/engine/rete/tms.py                    |      102 |        7 |     93% |34, 37, 90, 94, 169, 174, 183 |
| rdflib-reasoning-engine/src/rdflibr/engine/rete\_store.py                 |       86 |       15 |     83% |85, 92-93, 98, 102, 130, 142, 149, 160, 177, 181, 185, 189, 193, 197 |
| rdflib-reasoning-engine/src/rdflibr/engine/rules.py                       |       48 |        4 |     92% |11-12, 24, 32 |
| rdflib-reasoning-engine/src/rdflibr/engine/rulesets/\_\_init\_\_.py       |        2 |        0 |    100% |           |
| rdflib-reasoning-engine/src/rdflibr/engine/rulesets/rdfs.py               |       15 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflibr/middleware/\_\_init\_\_.py        |        5 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflibr/middleware/dataset\_middleware.py |      152 |       53 |     65% |132-151, 179, 183-184, 193-194, 203-210, 221-228, 237-263, 267-268, 272-282, 289-291, 354-358, 366-367, 375-376, 394-395 |
| rdflib-reasoning-middleware/src/rdflibr/middleware/dataset\_model.py      |      115 |       17 |     85% |46, 63, 73, 75-76, 80-85, 95, 278, 282, 306, 310, 316-317 |
| rdflib-reasoning-middleware/src/rdflibr/middleware/dataset\_state.py      |        2 |        0 |    100% |           |
| rdflib-reasoning-middleware/src/rdflibr/middleware/tracing.py             |       63 |        3 |     95% | 46, 89-90 |
| src/rdflib\_reasoning/\_\_init\_\_.py                                     |        0 |        0 |    100% |           |
| **TOTAL**                                                                 | **1451** |  **155** | **89%** |           |


## Setup coverage badge

Below are examples of the badges you can use in your main branch `README` file.

### Direct image

[![Coverage badge](https://raw.githubusercontent.com/kvjrhall/rdflib-reasoning/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/kvjrhall/rdflib-reasoning/blob/python-coverage-comment-action-data/htmlcov/index.html)

This is the one to use if your repository is private or if you don't want to customize anything.

### [Shields.io](https://shields.io) Json Endpoint

[![Coverage badge](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/kvjrhall/rdflib-reasoning/python-coverage-comment-action-data/endpoint.json)](https://htmlpreview.github.io/?https://github.com/kvjrhall/rdflib-reasoning/blob/python-coverage-comment-action-data/htmlcov/index.html)

Using this one will allow you to [customize](https://shields.io/endpoint) the look of your badge.
It won't work with private repositories. It won't be refreshed more than once per five minutes.

### [Shields.io](https://shields.io) Dynamic Badge

[![Coverage badge](https://img.shields.io/badge/dynamic/json?color=brightgreen&label=coverage&query=%24.message&url=https%3A%2F%2Fraw.githubusercontent.com%2Fkvjrhall%2Frdflib-reasoning%2Fpython-coverage-comment-action-data%2Fendpoint.json)](https://htmlpreview.github.io/?https://github.com/kvjrhall/rdflib-reasoning/blob/python-coverage-comment-action-data/htmlcov/index.html)

This one will always be the same color. It won't work for private repos. I'm not even sure why we included it.

## What is that?

This branch is part of the
[python-coverage-comment-action](https://github.com/marketplace/actions/python-coverage-comment)
GitHub Action. All the files in this branch are automatically generated and may be
overwritten at any moment.