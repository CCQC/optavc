How does Optavc Work?
=====================

Class Structure
---------------

This is an introduction to the Class Structure of OPTAVC with inheritance diagrams. Optavc uses the following high level
classes to organize and manage code. The logic for creating these objects can by found in `main.py`

Classes for Performing Calculations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Optimization
    Manages running optimizations through optking
* Calculation
    A base (abstract) class that defines the basic attributes and methods that higher level classes use
* AnalyticCalculation
    Another base class that provides basic functionality to SinglePoint, AnalyticGradient, and AnalyticHessian
    calculations and provides a unified interface so that running these calculations looks the same to
    FiniteDifferenceCalc classes
* SinglePoint
    Handles running individual energy calculations
* AnalyticGradient
* AnalyticHessian
* FiniteDifferenceCalc
    A base class for performing Gradient and Hessian calculations by finite differences using Psi4's findif objects
* Gradient
    Manages displacements and calculations for a gradient calculation by finite differences of energies
* Hessian
    Manages displacements and calculations for a Hessian calculation by finite differences of energies or gradients.

.. inheritance-diagram:: optavc.calculations.Calculation optavc.calculations.SinglePoint optavc.calculations.AnalyticCalc optavc.calculations.AnalyticGradient optavc.calculations.AnalyticHessian optavc.findifcalcs.FiniteDifferenceCalc optavc.findifcalcs.Gradient optavc.findifcalcs.Hessian optavc.xtpl.Procedure optavc.xtpl.Xtpl optavc.xtpl.Delta optavc.xtpl.XtplDelta optavc.optimize.Optimization optavc.options.Options optavc.molecule.Molecule optavc.cluster.Cluster optavc.template.InputFile
    :parts: 0

Low Level Classs
~~~~~~~~~~~~~~~~

* Options
    All of optavcs options. Provides defaults and type checking
* Molecule
    A Basic Molecule object
* InputFile
    This object reprents the molecule and calculation information obtained from the template file
    provided by the user


Calculation Classes
-------------------

.. automodule:: optavc.calculations
    :members:
    :noindex: optavc.calculations.Calculations.compute_result optavc.calculations.Calculations.get_result optavc.calculations.Calculations.run optavc.calculations.Calculations.write_input optavc.calculations.AnalyticCalc.compute_result optavc.calculations.AnalyticCalc.get_result optavc.calculations.AnalyticCalc.run optavc.calculations.AnalyticCalc.write_input


Finite Difference
-----------------
 
.. automodule:: optavc.findifcalcs
    :members:

Composite Procedures
--------------------

.. automodule:: optavc.xtpl
    :members:
    :noindex: optavc.xtpl.Xtpl.get_result

Optimization
------------

.. automodule:: optavc.optimize
    :members:
