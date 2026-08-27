# Verified definition of `R2`

## Parameters

- `n`: fixed at `4`
- `k`: fixed at `0`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n}-2,\mathit{k}}\left(\mathit{x},\mathit{z}\right) \land \mathtt{R2}_{\mathit{n}-2,\mathit{k}}\left(\mathit{z},\mathit{y}\right)\right)\right) \land \neg \left(\exists \mathit{w}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n}-3,\mathit{k}+1}\left(\mathit{x},\mathit{w}\right) \land \mathtt{R2}_{\mathit{n}-3,\mathit{k}+1}\left(\mathit{w},\mathit{y}\right)\right)\right)\right)
$$

## Candidate source

```text
(and (exists ((z Point)) (and (R2__n_2__k_0 x z) (R2__n_2__k_0 z y))) (not (exists ((w Point)) (and (R2__n_1__k_1 x w) (R2__n_1__k_1 w y)))))
```
