# Automorphisms of `D_{n,k}`

## Goal

Let `D_{n,k}` be the undirected relation on `Z^2` defined by

```text
D_{n,k}(u,v) iff v - u belongs to
S_{n,k} = {(±n,±k), (±k,±n)},
```

where the signs are chosen independently. Determine the automorphism group of
the graph induced on the reachability class `RC_{n,k}(0,0)`.

The expected result is

```text
Aut(RC_{n,k}(0,0), D_{n,k}) = L semidirect_product D4,
```

where `L = RC_{n,k}(0,0)` acts by translations and `D4` is the eight-element
symmetry group of the square. Since `L` is abstractly isomorphic to `Z^2`, this
can also be written as

```text
Aut(RC_{n,k}(0,0), D_{n,k})
    is isomorphic to Z^2 semidirect_product D4.
```

In particular, the stabilizer of `(0,0)` is exactly `D4`.

## Step 1: describe the reachability lattice

Set

```text
d = gcd(n,k),
p = n/d,
q = k/d.
```

By the reachability criterion already proved for `D_{n,k}`, the component of
the origin is the following rank-two lattice.

If `p` and `q` have opposite parity, then

```text
L = RC_{n,k}(0,0)
  = {(d*a,d*b) : a,b in Z}.
```

If `p` and `q` are both odd, then

```text
L = RC_{n,k}(0,0)
  = {(d*a,d*b) : a,b in Z and a = b mod 2}.
```

In both cases `L` is a free abelian group of rank two and hence isomorphic to
`Z^2`.

## Step 2: represent the component as a Cayley graph

All vectors in `S_{n,k}` belong to `L`, and they generate `L`. Therefore the
induced graph on the component is exactly

```text
Cay(L, S_{n,k}).
```

Here the vertices are the elements of the additive group `L`, and `u` and `v`
are adjacent exactly when `v - u` belongs to `S_{n,k}`.

## Step 3: prove that every automorphism is affine

Apply Theorem 1.4 of Morris, Morris, and Verret. The group `L` is torsion-free
and nilpotent because it is free abelian, while `S_{n,k}` is finite, symmetric,
and generates `L`. Consequently every automorphism of `Cay(L,S_{n,k})` has the
form

```text
f(v) = A(v) + t,
```

where

```text
t belongs to L,
A belongs to Aut(L),
A(S_{n,k}) = S_{n,k}.
```

Thus it remains to calculate the group of linear automorphisms preserving the
move set.

## Step 4: calculate the stabilizer of the move set

Every signed coordinate permutation preserves `S_{n,k}`. These eight maps are

```text
(x,y) -> ( x, y)
(x,y) -> (-x, y)
(x,y) -> ( x,-y)
(x,y) -> (-x,-y)
(x,y) -> ( y, x)
(x,y) -> (-y, x)
(x,y) -> ( y,-x)
(x,y) -> (-y,-x).
```

They form a subgroup isomorphic to `D4`.

To show that there are no additional linear automorphisms, assume first that
`0 < k < n`. The elements of `S_{n,k}` are the vertices of the convex octagon

```text
(n,k), (k,n), (-k,n), (-n,k),
(-n,-k), (-k,-n), (k,-n), (n,-k).
```

A linear transformation preserving `S_{n,k}` induces a combinatorial symmetry
of this octagon. The known `D4` subgroup consists of the symmetries that move a
vertex by an even number of positions in this cyclic ordering, together with
the corresponding reflections.

If there were a symmetry outside this subgroup, composing it with an element
of `D4` would give a one-position cyclic shift. Such a linear map would satisfy

```text
(n,k) -> (k,n),
(k,n) -> (-k,n),
(-k,n) -> (-n,k).
```

The first two images determine the linear map. Requiring the third image gives

```text
n^2 - 2*n*k - k^2 = 0,
```

and therefore

```text
n/k = 1 + sqrt(2).
```

This is impossible for positive integers `n` and `k`. Hence there is no
one-position shift and no symmetry outside `D4`. Therefore

```text
{A in Aut(L) : A(S_{n,k}) = S_{n,k}} = D4.
```

The degenerate cases `k = 0` and `k = n`, if they are included in the chosen
definition, reduce directly to the ordinary square grid on a suitable lattice;
their component automorphism group has the same abstract form.

## Step 5: assemble the automorphism group

Translations by elements of `L` form a normal subgroup of the automorphism
group. Every automorphism has a unique decomposition

```text
v -> A(v) + t,
```

with `t in L` and `A in D4`. Composition is given by

```text
(t,A) * (u,B) = (t + A(u), A*B).
```

It follows that

```text
Aut(RC_{n,k}(0,0), D_{n,k}) = L semidirect_product D4.
```

An automorphism fixes `(0,0)` exactly when `t = 0`, so

```text
Stab((0,0)) = D4.
```

## Source for the affine-automorphism theorem

Dave Witte Morris, Joy Morris, and Gabriel Verret,
“Isomorphisms of Cayley graphs on nilpotent groups,”
New York Journal of Mathematics 22 (2016), 453–467.

The relevant statement is Theorem 1.4; Proposition 2.1 records the special case
of torsion-free abelian groups.

```text
https://nyjm.albany.edu/j/2016/22-21v.pdf
```
