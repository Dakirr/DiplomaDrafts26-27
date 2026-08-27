# Verified definition of `R2`

## Parameters

- `n`: fixed at `3`
- `k`: fixed at `0`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\exists \mathit{w}\in\mathbb{Z}^{2}\;\left(\mathtt{R1}\left(\mathit{x},\mathit{z}\right) \land \mathtt{R2}_{\mathit{n}-1,\mathit{k}}\left(\mathit{z},\mathit{y}\right) \land \mathtt{R1}\left(\mathit{z},\mathit{w}\right) \land \mathtt{R2}_{\mathit{n}-1,\mathit{k}}\left(\mathit{x},\mathit{w}\right) \land \mathtt{R1}\left(\mathit{w},\mathit{y}\right)\right)\right)
$$

## Candidate source

```text
(exists ((z Point) (w Point)) (and (R1 x z) (R2__n_2__k_0 z y) (R1 z w) (R2__n_2__k_0 x w) (R1 w y)))
```
