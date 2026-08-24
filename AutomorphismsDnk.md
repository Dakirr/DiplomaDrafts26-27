# Automorphisms of the all-reaching knight graph and the square grid

## 1. Aim and assumptions

Let $n$ and $k$ be distinct positive integers. Define the generalized
knight relation on $\mathbb Z^2$ by

$$
D_{n,k}(x,y)
\quad\Longleftrightarrow\quad
y-x\in S_{n,k},
$$

where

$$
S_{n,k}
=
\{(\pm n,\pm k),(\pm k,\pm n)\}.
$$

The two signs in each vector are chosen independently.

Define the ordinary square-grid relation by

$$
E(x,y)
\quad\Longleftrightarrow\quad
y-x\in T,
$$

where

$$
T=\{(1,0),(-1,0),(0,1),(0,-1)\}.
$$

Assume that $D_{n,k}$ reaches every point of $\mathbb Z^2$. By the
reachability criterion, this is equivalent to

$$
\gcd(n,k)=1
\qquad\text{and}\qquad
n+k\equiv 1\pmod 2.
$$

The goal is to prove the following equality of concrete permutation groups:

$$
\operatorname{Aut}(\mathbb Z^2,D_{n,k})
=
\operatorname{Aut}(\mathbb Z^2,E)
=
\{x\mapsto Ax+t:t\in\mathbb Z^2,\ A\in D_4\}.
$$

Here $D_4$ is the group of the eight signed coordinate permutations. The
word “equality” is important: the two automorphism groups contain exactly the
same permutations of the same set $\mathbb Z^2$; they are not merely
abstractly isomorphic.

After this, pass to a common upward completion and prove

$$
\operatorname{Aut}((\mathbb Z^2)^*,D_{n,k}^*)
=
\operatorname{Aut}((\mathbb Z^2)^*,E^*).
$$

The upward-complete version of the Svenonius criterion will then imply that
$D_{n,k}$ and $E$ are first-order interdefinable without parameters.

This does **not** say that the two graphs are isomorphic. The square grid has
degree $4$, whereas the graph of $D_{n,k}$ has degree $8$ under the
assumptions above. Isomorphism preserves degrees.

## 2. Regard the relations as Cayley graphs

The graph of $D_{n,k}$ is

$$
\operatorname{Cay}(\mathbb Z^2,S_{n,k}).
$$

The all-reaching assumption says precisely that $S_{n,k}$ generates the
additive group $\mathbb Z^2$, so this Cayley graph is connected.

Similarly, the square grid is

$$
\operatorname{Cay}(\mathbb Z^2,T),
$$

and $T$ generates $\mathbb Z^2$.

Both graphs are therefore connected finite-valency Cayley graphs of the
torsion-free abelian group $\mathbb Z^2$. In particular, $\mathbb Z^2$ is
torsion-free nilpotent, so the affine-automorphism theorem for such Cayley
graphs applies.

## 3. Every automorphism of $D_{n,k}$ is affine

Apply [Theorem 1.4 of Morris, Morris, and Verret](https://nyjm.albany.edu/j/2016/22-21v.pdf) to
$\operatorname{Cay}(\mathbb Z^2,S_{n,k})$. Every automorphism has the form

$$
f(x)=Ax+t,
$$

where

$$
t\in\mathbb Z^2,\qquad
A\in\operatorname{GL}(2,\mathbb Z),\qquad
A(S_{n,k})=S_{n,k}.
$$

Thus $A$ is not a vector. It is a fixed $2\times2$ integer matrix, or
equivalently the linear part of $f$. The symbol $t$ denotes the fixed
translation vector. Both $A$ and $t$ are fixed once the automorphism $f$
is fixed.

It remains to calculate the linear stabilizer

$$
G_{n,k}
=
\{A\in\operatorname{GL}(2,\mathbb Z):A(S_{n,k})=S_{n,k}\}.
$$

## 4. The linear stabilizer of the knight moves is $D_4$

### 4.1. The evident eight transformations

Every signed coordinate permutation preserves $S_{n,k}$. They are

$$
\begin{aligned}
(x,y)&\mapsto ( x, y),&
(x,y)&\mapsto (-x, y),\\
(x,y)&\mapsto ( x,-y),&
(x,y)&\mapsto (-x,-y),\\
(x,y)&\mapsto ( y, x),&
(x,y)&\mapsto (-y, x),\\
(x,y)&\mapsto ( y,-x),&
(x,y)&\mapsto (-y,-x).
\end{aligned}
$$

These transformations form the square-symmetry group $D_4$. Hence

$$
D_4\leq G_{n,k}.
$$

### 4.2. Exclude all additional transformations

After interchanging $n$ and $k$ if necessary, suppose that $n>k>0$. In
cyclic order, the vectors of $S_{n,k}$ are the vertices of the convex
octagon

$$
\begin{aligned}
v_0&=( n, k),& v_1&=( k, n),&
v_2&=(-k, n),& v_3&=(-n, k),\\
v_4&=(-n,-k),& v_5&=(-k,-n),&
v_6&=( k,-n),& v_7&=( n,-k).
\end{aligned}
$$

Any invertible linear map preserving $S_{n,k}$ also preserves its convex
hull. It therefore induces a combinatorial symmetry of this octagon.

The known $D_4$ acts faithfully on the octagon and gives an eight-element
subgroup of its sixteen-element combinatorial symmetry group. It contains the
rotations through an even number of vertex positions and four reflections;
it therefore has index two. The one-position rotation is not in this
subgroup.

Consequently, if a linear symmetry outside $D_4$ existed, composing it with
an element of $D_4$ would produce the one-position shift

$$
v_0\mapsto v_1,\qquad
v_1\mapsto v_2,\qquad
v_2\mapsto v_3.
$$

The first two images determine a unique linear map, because $v_0$ and
$v_1$ are linearly independent. Requiring the same map to send $v_2$ to
$v_3$ gives

$$
n^2-2nk-k^2=0.
$$

Since $k>0$, this implies

$$
\frac nk=1+\sqrt2,
$$

which is impossible because $n/k$ is rational. Therefore no such additional
linear symmetry exists, and

$$
G_{n,k}=D_4.
$$

## 5. Automorphisms of the knight graph

Combining the affine theorem with the calculation of the linear stabilizer,
every automorphism of the all-reaching knight graph is uniquely of the form

$$
f(x)=Ax+t,
\qquad
t\in\mathbb Z^2,
\qquad
A\in D_4.
$$

Conversely, every such map is an automorphism, because

$$
f(y)-f(x)=A(y-x)
$$

and $A$ permutes the vectors in $S_{n,k}$.

Therefore

$$
\operatorname{Aut}(\mathbb Z^2,D_{n,k})
=
\mathbb Z^2\rtimes D_4.
$$

The composition rule is

$$
(t,A)(u,B)=(t+Au,AB).
$$

The translations form the normal subgroup $\mathbb Z^2$, and the stabilizer
of the origin is exactly $D_4$.

## 6. Automorphisms of the square grid

Apply the same affine theorem to
$\operatorname{Cay}(\mathbb Z^2,T)$. Every grid automorphism has the form

$$
f(x)=Ax+t,
$$

where $t\in\mathbb Z^2$ and $A(T)=T$. A linear map permutes the four
vectors of $T$ exactly when $A$ is a signed coordinate permutation. Hence

$$
\operatorname{Aut}(\mathbb Z^2,E)
=
\{x\mapsto Ax+t:t\in\mathbb Z^2,\ A\in D_4\}
=
\mathbb Z^2\rtimes D_4.
$$

More explicitly, if $E(x,y)$, then

$$
y-x\in\{\pm(1,0),\pm(0,1)\}.
$$

For $f(x)=Ax+t$, the translation cancels in the difference:

$$
f(y)-f(x)=A(y-x).
$$

Since $A\in D_4$, it permutes the four grid steps, and so
$E(f(x),f(y))$ holds. This is why every affine map obtained above preserves
$E$. An arbitrary matrix in $\operatorname{GL}(2,\mathbb Z)$ would not
necessarily preserve $E$; the restriction $A\in D_4$ is essential.

We have now proved equality as permutation groups on $\mathbb Z^2$:

$$
\operatorname{Aut}(\mathbb Z^2,D_{n,k})
=
\operatorname{Aut}(\mathbb Z^2,E).
$$

## 7. Construct a common upward completion

Let

$$
U=\mathbb Z^2\times\mathbb N.
$$

Think of $\mathbb Z^2\times\{i\}$ as the $i$-th galaxy. Define both
relations componentwise:

$$
D_{n,k}^*((x,i),(y,j))
\quad\Longleftrightarrow\quad
i=j\ \land\ D_{n,k}(x,y),
$$

and

$$
E^*((x,i),(y,j))
\quad\Longleftrightarrow\quad
i=j\ \land\ E(x,y).
$$

Thus each structure is a countable disjoint union of copies of its original
connected graph.

Connected locally finite vertex-transitive graphs fall under the
strongly-discretely-homogeneous case treated by Semenov and Soprunov. Their
upward completion is a countable disjoint union of isomorphic galaxies.
Consequently the structures just defined may be used as upward completions of
the all-reaching knight graph and of the square grid. The first galaxy embeds
as an elementary substructure.

For complete rigor in the final text, cite the result of Semenov and Soprunov
which identifies this disjoint union as the upward completion and gives the
automorphism/definability criterion for upward-complete structures.

## 8. Calculate the automorphisms of the completions

An automorphism of either completion may:

1. permute the galaxies by an arbitrary
   $\sigma\in\operatorname{Sym}(\mathbb N)$;
2. apply an arbitrary base automorphism $h_i$ inside each source galaxy
   $i$.

It therefore has the form

$$
F(x,i)=(h_i(x),\sigma(i)).
$$

Let

$$
H=\{x\mapsto Ax+t:t\in\mathbb Z^2,\ A\in D_4\}.
$$

Sections 5 and 6 proved, as a concrete equality, that

$$
\operatorname{Aut}(\mathbb Z^2,D_{n,k})
=H
=\operatorname{Aut}(\mathbb Z^2,E).
$$

It follows that the two sets of allowed maps $F$ are exactly the same:

$$
\operatorname{Aut}(U,D_{n,k}^*)
=
H\mathbin{\wr}\operatorname{Sym}(\mathbb N)
=
\operatorname{Aut}(U,E^*).
$$

Equivalently,

$$
\operatorname{Aut}(U,D_{n,k}^*)
=
H^{\mathbb N}\rtimes\operatorname{Sym}(\mathbb N)
=
\operatorname{Aut}(U,E^*).
$$

Again, this is equality of concrete permutation groups on the common universe
$U$, not only an abstract group isomorphism.

## 9. Apply the upward-complete Svenonius criterion

Use the automorphism/definability theorem for upward-complete structures:

> A relation $R$ is first-order definable without parameters from a
> structure $M$ if and only if $R^*$ is preserved by every
> automorphism of an upward completion $M^*$.

Apply it in both directions.

First,

$$
\operatorname{Aut}(U,D_{n,k}^*)
\leq
\operatorname{Aut}(U,E^*),
$$

so every automorphism of the upward completion of $D_{n,k}$ preserves
$E^*$. Therefore $E$ is first-order definable from $D_{n,k}$
without parameters.

Second,

$$
\operatorname{Aut}(U,E^*)
\leq
\operatorname{Aut}(U,D_{n,k}^*),
$$

so every automorphism of the upward completion of $E$ preserves
$D_{n,k}^*$. Therefore $D_{n,k}$ is first-order definable from
$E$ without parameters.

Hence

$$
(\mathbb Z^2,D_{n,k})
\quad\text{and}\quad
(\mathbb Z^2,E)
$$

are first-order interdefinable.

They still are not isomorphic as graphs: interdefinability means that each
edge relation can be described by a first-order formula using the other edge
relation on the same universe. It does not mean that the two edge relations
are carried to one another by a bijection.

## 10. Logical dependency of the proof

1. $D_{n,k}$ is all-reaching.
2. Therefore $\operatorname{Cay}(\mathbb Z^2,S_{n,k})$ is connected.
3. The Morris--Morris--Verret theorem makes every automorphism affine.
4. The linear stabilizer of $S_{n,k}$ is exactly $D_4$.
5. Hence
   $\operatorname{Aut}(\mathbb Z^2,D_{n,k})
   =\mathbb Z^2\rtimes D_4$.
6. Independently,
   $\operatorname{Aut}(\mathbb Z^2,E)
   =\mathbb Z^2\rtimes D_4$, with exactly the same permutations.
7. Their upward completions therefore have the same wreath-product
   automorphism group.
8. The upward-complete Svenonius criterion yields first-order
   interdefinability.

## 11. Sources to cite

For the affine form of automorphisms of connected Cayley graphs on
torsion-free nilpotent groups:

> Dave Witte Morris, Joy Morris, and Gabriel Verret,
> “Isomorphisms of Cayley graphs on nilpotent groups,”
> *New York Journal of Mathematics* 22 (2016), 453--467.
> Theorem 1.4; see also Proposition 2.1 for the torsion-free abelian case.
> <https://nyjm.albany.edu/j/2016/22-21v.pdf>

For upward-complete structures, their galaxy decomposition, and the
automorphism criterion for definability:

> A. Semenov and S. Soprunov,
> “Automorphisms and Definability (of Reducts) for Upward Complete
> Structures,” *Mathematics* 10(20) (2022), Article 3748.
> <https://doi.org/10.3390/math10203748>

## 12. Variant for a non-all-reaching knight relation

If the all-reaching assumption is removed, first restrict to

$$
L=\operatorname{RC}_{n,k}(0,0).
$$

Set

$$
d=\gcd(n,k),\qquad p=\frac nd,\qquad q=\frac kd.
$$

If $p$ and $q$ have opposite parity, then

$$
L=d\mathbb Z^2.
$$

If $p$ and $q$ are both odd, then

$$
L
=
\{(da,db):a,b\in\mathbb Z,\ a\equiv b\pmod 2\}.
$$

In either case $L$ is a rank-two free abelian group, and the component is
$\operatorname{Cay}(L,S_{n,k})$. The same affine argument gives

$$
\operatorname{Aut}(\operatorname{RC}_{n,k}(0,0),D_{n,k})
=
L\rtimes D_4
$$

for distinct positive $n$ and $k$. The main interdefinability argument
above, however, uses the all-reaching case so that both relations live on the
same standard universe $\mathbb Z^2$ and have the same concrete affine
automorphisms.
