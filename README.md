# optavc

In order to run this, you must have Psi4 installed as an importable Python
module.  Instructions can be found on the Psi4 wiki page
[8_FAQ_Contents](https://github.com/psi4/psi4/wiki/8_FAQ_Contents).

This will generate a psi4.so file in /path/to/psi4/obj/bin/, so you must add
that directory to your PYTHONPATH to make Python aware of its existence.

The directory containing this package must also be added to your PYTHONPATH, in
which case the modules are importable as follows.

```python
import optavc.<module name>
```

This version works with latest Psi4 with findif overhaul -jdw 8-31-18
