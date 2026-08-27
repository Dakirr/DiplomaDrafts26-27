# Verified definition of `R2`

## Parameters

- `n`: fixed at `2`
- `k`: fixed at `2`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n}-1,\mathit{k}-1}\left(\mathit{x},\mathit{z}\right) \land \mathtt{R2}_{\mathit{n}-1,\mathit{k}-1}\left(\mathit{z},\mathit{y}\right)\right)\right) \land \neg \left(\mathit{x} = \mathit{y}\right) \land \neg \mathtt{R2}_{\mathit{n}-2,\mathit{k}}\left(\mathit{x},\mathit{y}\right)\right)
$$

## Candidate source

```text
(and (exists ((z Point)) (and (R2__n_1__k_1 x z) (R2__n_1__k_1 z y))) (not (= x y)) (not (R2__n_0__k_2 x y)))
```
