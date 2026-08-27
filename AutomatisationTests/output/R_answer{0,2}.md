# Verified definition of `R2`

## Parameters

- `n`: fixed at `0`
- `k`: fixed at `2`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\left(\mathtt{R1}\left(\mathit{x},\mathit{z}\right) \land \mathtt{R1}\left(\mathit{z},\mathit{y}\right) \land \left(\forall \mathit{w}\in\mathbb{Z}^{2}\;\left(\left(\mathtt{R1}\left(\mathit{x},\mathit{w}\right) \land \mathtt{R1}\left(\mathit{w},\mathit{y}\right)\right) \longrightarrow \left(\mathit{w} = \mathit{z}\right)\right)\right)\right)\right)
$$

## Candidate source

```text
(exists ((z Point)) (and (R1 x z) (R1 z y) (forall ((w Point)) (=> (and (R1 x w) (R1 w y)) (= w z)))))
```
