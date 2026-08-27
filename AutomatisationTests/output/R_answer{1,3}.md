# Verified definition of `R2`

## Parameters

- `n`: fixed at `1`
- `k`: fixed at `3`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n}-1,\mathit{k}}\left(\mathit{x},\mathit{z}\right) \land \mathtt{R1}\left(\mathit{z},\mathit{y}\right)\right)\right) \land \left(\exists \mathit{w}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n},\mathit{k}-1}\left(\mathit{x},\mathit{w}\right) \land \mathtt{R1}\left(\mathit{w},\mathit{y}\right)\right)\right) \land \neg \mathtt{R2}_{\mathit{n}-1,\mathit{k}-1}\left(\mathit{x},\mathit{y}\right)\right)
$$

## Candidate source

```text
(and (exists ((z Point)) (and (R2__n_0__k_3 x z) (R1 z y))) (exists ((w Point)) (and (R2__n_1__k_2 x w) (R1 w y))) (not (R2__n_0__k_2 x y)))
```
