# Verified definition of `R2`

## Parameters

- `n`: fixed at `2`
- `k`: fixed at `4`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n}-2,\mathit{k}-2}\left(\mathit{x},\mathit{z}\right) \land \mathtt{R2}_{\mathit{n},\mathit{k}-2}\left(\mathit{z},\mathit{y}\right)\right)\right) \land \neg \mathtt{R2}_{\mathit{n},\mathit{k}-4}\left(\mathit{x},\mathit{y}\right)\right)
$$

## Candidate source

```text
(and (exists ((z Point)) (and (R2__n_0__k_2 x z) (R2__n_2__k_2 z y))) (not (R2__n_2__k_0 x y)))
```
