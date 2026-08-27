# Verified definition of `R2`

## Parameters

- `n`: fixed at `2`
- `k`: fixed at `1`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\neg \mathtt{R1}\left(\mathit{x},\mathit{y}\right) \land \left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n}-2,\mathit{k}+1}\left(\mathit{x},\mathit{z}\right) \land \mathtt{R1}\left(\mathit{z},\mathit{y}\right)\right)\right) \land \left(\exists \mathit{w}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n}-1,\mathit{k}}\left(\mathit{x},\mathit{w}\right) \land \mathtt{R1}\left(\mathit{w},\mathit{y}\right)\right)\right)\right)
$$

## Candidate source

```text
(and (not (R1 x y)) (exists ((z Point)) (and (R2__n_0__k_2 x z) (R1 z y))) (exists ((w Point)) (and (R2__n_1__k_1 x w) (R1 w y))))
```
