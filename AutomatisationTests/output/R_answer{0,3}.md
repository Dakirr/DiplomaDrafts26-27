# Verified definition of `R2`

## Parameters

- `n`: fixed at `0`
- `k`: fixed at `3`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\exists \mathit{w}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n},\mathit{k}-1}\left(\mathit{x},\mathit{z}\right) \land \mathtt{R1}\left(\mathit{z},\mathit{y}\right) \land \mathtt{R1}\left(\mathit{x},\mathit{w}\right) \land \mathtt{R2}_{\mathit{n},\mathit{k}-1}\left(\mathit{w},\mathit{y}\right) \land \mathtt{R1}\left(\mathit{z},\mathit{w}\right)\right)\right)
$$

## Candidate source

```text
(exists ((z Point) (w Point)) (and (R2__n_0__k_2 x z) (R1 z y) (R1 x w) (R2__n_0__k_2 w y) (R1 z w)))
```
