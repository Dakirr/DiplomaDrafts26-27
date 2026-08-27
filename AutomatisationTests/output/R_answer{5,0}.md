# Verified definition of `R2`

## Parameters

- `n`: fixed at `5`
- `k`: fixed at `0`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n}-1,\mathit{k}}\left(\mathit{x},\mathit{z}\right) \land \mathtt{R1}\left(\mathit{z},\mathit{y}\right)\right)\right) \land \neg \mathtt{R2}_{\mathit{n}-2,\mathit{k}}\left(\mathit{x},\mathit{y}\right) \land \neg \left(\exists \mathit{w}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n}-3,\mathit{k}+2}\left(\mathit{x},\mathit{w}\right) \land \mathtt{R2}_{\mathit{n}-3,\mathit{k}+1}\left(\mathit{w},\mathit{y}\right)\right)\right)\right)
$$

## Candidate source

```text
(and (exists ((z Point)) (and (R2__n_4__k_0 x z) (R1 z y))) (not (R2__n_3__k_0 x y)) (not (exists ((w Point)) (and (R2__n_2__k_2 x w) (R2__n_2__k_1 w y)))))
```
