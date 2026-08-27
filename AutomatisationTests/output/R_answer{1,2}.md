# Verified definition of `R2`

## Parameters

- `n`: fixed at `1`
- `k`: fixed at `2`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\neg \mathtt{R1}\left(\mathit{x},\mathit{y}\right) \land \left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n},\mathit{k}-1}\left(\mathit{x},\mathit{z}\right) \land \mathtt{R1}\left(\mathit{z},\mathit{y}\right)\right)\right)\right)
$$

## Candidate source

```text
(and (not (R1 x y)) (exists ((z Point)) (and (R2__n_1__k_1 x z) (R1 z y))))
```
