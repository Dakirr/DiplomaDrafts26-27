# Verified definition of `R2`

## Parameters

- `n`: fixed at `0`
- `k`: fixed at `6`

## Verified equivalence

$$
\mathtt{R2}_{\mathit{n},\mathit{k}}\left(\mathit{x},\mathit{y}\right) \Leftrightarrow \left(\left(\exists \mathit{z}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n},\mathit{k}-3}\left(\mathit{x},\mathit{z}\right) \land \mathtt{R2}_{\mathit{n},\mathit{k}-3}\left(\mathit{z},\mathit{y}\right)\right)\right) \land \left(\exists \mathit{w}\in\mathbb{Z}^{2}\;\left(\mathtt{R2}_{\mathit{n},\mathit{k}-4}\left(\mathit{x},\mathit{w}\right) \land \mathtt{R2}_{\mathit{n},\mathit{k}-2}\left(\mathit{w},\mathit{y}\right)\right)\right)\right)
$$

## Candidate source

```text
(and (exists ((z Point)) (and (R2__n_0__k_3 x z) (R2__n_0__k_3 z y))) (exists ((w Point)) (and (R2__n_0__k_2 x w) (R2__n_0__k_4 w y))))
```
