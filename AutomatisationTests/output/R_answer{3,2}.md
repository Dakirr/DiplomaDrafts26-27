# Verified definition of `R2`

## Parameters

- `n`: fixed at `3`
- `k`: fixed at `2`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n}-1,\mathit{k}}\left(\mathit{x},\mathit{z}\right) \land \mathtt{R1}\left(\mathit{z},\mathit{y}\right)\right)\right) \land \neg \mathtt{R2}_{\mathit{n}-1,\mathit{k}-1}\left(\mathit{x},\mathit{y}\right)\right)
$$

## Candidate source

```text
(and (exists ((z Point)) (and (R2__n_2__k_2 x z) (R1 z y))) (not (R2__n_2__k_1 x y)))
```
