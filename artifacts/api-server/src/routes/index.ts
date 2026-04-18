import { Router, type IRouter } from "express";
import healthRouter from "./health";
import mojitoRouter from "./mojito";

const router: IRouter = Router();

router.use(healthRouter);
router.use(mojitoRouter);

export default router;
